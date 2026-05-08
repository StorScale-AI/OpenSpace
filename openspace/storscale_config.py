"""StorScale agent -> OpenSpace category mappings and evolution thresholds."""
from __future__ import annotations

# Mapping from agent slug (must match the directory name under
# storscale-agents/storscale-agents/agents/) to a skill category. Agents
# without an entry here fall through to "no skill selected" — they still
# run, just without an OpenSpace-managed skill injection.
#
# When a new agent is added to storscale-agents, add its slug here so it
# becomes eligible for skill evolution. Agents that should bypass evolution
# entirely (e.g. deterministic monitors) belong in SKIP_AGENTS below.
AGENT_CATEGORIES: dict[str, str] = {
    # Acquisition
    "prospector": "acquisition",
    "due-diligence": "acquisition",
    # Financial analysis
    "valuation": "financial_analysis",
    "financial-modelling": "financial_analysis",
    # Investor / legal
    "investor-relations": "investor_comms",
    "legal": "legal",
    # Operations
    "post-acquisition-ops": "operations",
    # Market analysis
    "aggregator-intelligence": "market_analysis",
    # SEO / content
    "seo-agent": "seo_content",
    "storscale-seo": "seo_content",
    "content-creation": "seo_content",
    "website-optimizer": "seo_content",
    # Advertising
    "ad-agent": "advertising",
    # Reputation / reviews
    "review-reputation": "reputation",
    "review-intelligence": "reputation",
    # Marketplace
    "sparefoot-optimizer": "marketplace",
    "marketplace-strategy": "marketplace",
    # Customer ops
    "customer-success": "customer_ops",
    "customer-care": "customer_ops",
    "churn-prevention": "customer_ops",
    "onboarding": "customer_ops",
    # Pricing
    "dynamic-pricing": "pricing",
    "competitor-rate-watcher": "pricing",
    "pricing-recommendation-watcher": "pricing",
    # Sales
    "outbound-sales": "sales",
    "lead-nurture": "sales",
    # DevOps / resilience
    "resiliency": "devops",
    # Knowledge / intelligence
    "knowledge-evolution": "knowledge",
    "revenue-intelligence": "intelligence",
    "channel-attribution": "intelligence",
    "demand-forecasting": "intelligence",
    "performance-digest": "intelligence",
    # NOTE: pm-sprint-advisor is intentionally omitted pending categorization.
    # Add it here when its category is decided (likely "operations" or a new
    # "engineering_ops" category).
}

# Agents to exclude from OpenSpace skill injection. Use this for agents
# that are pure deterministic logic (no Claude prompt to evolve) or that
# have safety-sensitive side effects we don't want auto-tuned.
SKIP_AGENTS = {"deployment-monitor", "data-quality-monitor"}

# Evolution thresholds
ANALYSIS_EVERY_N_RUNS = 5
FIX_THRESHOLD = 0.6
CAPTURE_IMPROVEMENT_THRESHOLD = 0.15
DERIVE_THRESHOLD = 0.8
