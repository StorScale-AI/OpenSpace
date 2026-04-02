"""StorScale adapter — bridges OpenSpace skill engine with StorScale agents via Supabase."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from supabase import create_client, Client

from openspace.storscale_config import (
    AGENT_CATEGORIES,
    SKIP_AGENTS,
    ANALYSIS_EVERY_N_RUNS,
    FIX_THRESHOLD,
    CAPTURE_IMPROVEMENT_THRESHOLD,
    DERIVE_THRESHOLD,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

AGENTS_ROOT: Path = (
    Path(os.environ["AGENTS_ROOT"])
    if "AGENTS_ROOT" in os.environ
    else Path(__file__).resolve().parent.parent / "storscale-agents" / "agents"
)

# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------


def _get_supabase_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def _best_skill(
    client: Client, category: str, facility_id: str | None
) -> dict[str, Any] | None:
    """Return the highest-scoring active skill for the given category."""
    query = (
        client.table("agent_skills")
        .select("*")
        .eq("category", category)
        .eq("is_active", True)
        .order("score", desc=True)
        .limit(1)
    )
    # Prefer facility-specific skill; fall back to NULL facility
    if facility_id:
        # Try facility-specific first
        result = (
            client.table("agent_skills")
            .select("*")
            .eq("category", category)
            .eq("is_active", True)
            .eq("facility_id", facility_id)
            .order("score", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]

    # Fall back to global skill (facility_id IS NULL)
    result = (
        client.table("agent_skills")
        .select("*")
        .eq("category", category)
        .eq("is_active", True)
        .is_("facility_id", "null")
        .order("score", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def _update_skill_stats(
    client: Client,
    skill_id: str,
    success: bool,
    improvement: float | None,
) -> None:
    """Increment counters and recompute effective_rate / score."""
    existing = (
        client.table("agent_skills").select("*").eq("id", skill_id).single().execute()
    )
    if not existing.data:
        return

    row: dict[str, Any] = existing.data
    total_selections: int = (row.get("total_selections") or 0) + 1
    total_applied: int = (row.get("total_applied") or 0) + 1
    total_completions: int = (row.get("total_completions") or 0) + (1 if success else 0)
    total_fallbacks: int = (row.get("total_fallbacks") or 0) + (0 if success else 1)
    effective_rate: float = (
        total_completions / total_applied if total_applied > 0 else 0.0
    )

    # Simple score: effective_rate, nudged by improvement delta
    base_score: float = effective_rate
    if improvement is not None:
        base_score = min(1.0, base_score + improvement * CAPTURE_IMPROVEMENT_THRESHOLD)
    score = round(base_score, 4)

    client.table("agent_skills").update(
        {
            "total_selections": total_selections,
            "total_applied": total_applied,
            "total_completions": total_completions,
            "total_fallbacks": total_fallbacks,
            "effective_rate": effective_rate,
            "score": score,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", skill_id).execute()

    # Periodic analysis snapshot
    if total_selections % ANALYSIS_EVERY_N_RUNS == 0:
        _record_analysis(client, row, total_selections, effective_rate, score)


def _record_analysis(
    client: Client,
    skill_row: dict[str, Any],
    total_selections: int,
    effective_rate: float,
    score: float,
) -> None:
    """Insert a basic analysis record into skill_analyses."""
    analysis = {
        "skill_id": skill_row["id"],
        "category": skill_row.get("category"),
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "total_selections": total_selections,
        "effective_rate": effective_rate,
        "score": score,
        "fix_threshold": FIX_THRESHOLD,
        "derive_threshold": DERIVE_THRESHOLD,
        "needs_fix": effective_rate < FIX_THRESHOLD,
        "ready_to_derive": score >= DERIVE_THRESHOLD,
    }
    client.table("skill_analyses").insert(analysis).execute()


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------

_MARKER = "__OPENSPACE_OUTPUT__"


def _parse_output(stdout: str) -> dict[str, Any] | None:
    """Extract structured JSON following the __OPENSPACE_OUTPUT__ marker."""
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith(_MARKER):
            payload = stripped[len(_MARKER):].strip()
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                return None
    return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="StorScale OpenSpace adapter — selects skills, shells out to Node agents."
    )
    p.add_argument("--agent", required=True, help="Agent slug (e.g. prospector)")
    p.add_argument("--facility", default=None, help="Facility UUID (optional)")
    p.add_argument("--options", default=None, help="JSON string of extra options")
    p.add_argument("--task-id", default=None, dest="task_id", help="Task ID for tracking")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    agent_slug: str = args.agent
    facility_id: str | None = args.facility
    raw_options: str | None = args.options
    task_id: str | None = args.task_id

    # ------------------------------------------------------------------
    # Skip deterministic agents
    # ------------------------------------------------------------------
    if agent_slug in SKIP_AGENTS:
        print(
            f"[storscale-adapter] Agent '{agent_slug}' is deterministic — skipping OpenSpace skill selection.",
            flush=True,
        )
        return 0

    # ------------------------------------------------------------------
    # Supabase
    # ------------------------------------------------------------------
    client = _get_supabase_client()

    category = AGENT_CATEGORIES.get(agent_slug)
    skill: dict[str, Any] | None = None
    if category:
        skill = _best_skill(client, category, facility_id)

    # ------------------------------------------------------------------
    # Build skill-context payload
    # ------------------------------------------------------------------
    skill_context: dict[str, Any] = {
        "agent": agent_slug,
        "facility_id": facility_id,
        "task_id": task_id,
        "category": category,
    }
    if skill:
        skill_context["skill_id"] = skill["id"]
        skill_context["skill_name"] = skill.get("name")
        skill_context["skill_prompt"] = skill.get("prompt")
        skill_context["skill_score"] = skill.get("score")

    # ------------------------------------------------------------------
    # Shell out to Node agent
    # ------------------------------------------------------------------
    agent_entry = AGENTS_ROOT / agent_slug / "index.js"
    cmd: list[str] = [
        "node",
        str(agent_entry),
        "--skill-context",
        json.dumps(skill_context),
    ]
    if raw_options:
        cmd += ["--options", raw_options]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,
    )

    # Forward agent stdout/stderr to our own streams
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)

    # ------------------------------------------------------------------
    # Parse structured output
    # ------------------------------------------------------------------
    parsed_output = _parse_output(result.stdout or "")
    success = result.returncode == 0
    improvement: float | None = None
    if parsed_output and isinstance(parsed_output, dict):
        improvement = parsed_output.get("improvement_delta")

    # ------------------------------------------------------------------
    # Update skill stats if a skill was used
    # ------------------------------------------------------------------
    if skill:
        _update_skill_stats(client, skill["id"], success, improvement)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
