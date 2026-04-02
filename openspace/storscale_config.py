"""StorScale agent -> OpenSpace category mappings and evolution thresholds."""
from __future__ import annotations

AGENT_CATEGORIES: dict[str, str] = {
    "prospector": "acquisition",
    "due-diligence": "acquisition",
    "valuation": "financial_analysis",
    "financial-model": "financial_analysis",
    "investor-relations": "investor_comms",
    "legal": "legal",
    "post-acq-ops": "operations",
    "market-scanner": "market_analysis",
    "seo": "seo_content",
    "content": "seo_content",
    "ads": "advertising",
    "reputation": "reputation",
    "sparefoot-optimizer": "marketplace",
    "customer-success": "customer_ops",
    "website-optimizer": "seo_content",
    "dynamic-pricing": "pricing",
    "outreach": "sales",
    "conversion": "sales",
    "resiliency-security": "devops",
    "knowledge-evolution": "knowledge",
    "revenue-intelligence": "intelligence",
    "channel-attribution": "intelligence",
    "demand-forecasting": "intelligence",
    "performance-digest": "intelligence",
    "reputation-intelligence": "reputation",
    "lead-nurture": "sales",
    "storscale-seo": "seo_content",
    "churn-prevention": "customer_ops",
    "aggregator-intelligence": "market_analysis",
}

SKIP_AGENTS = {"deployment-monitor", "data-quality-monitor"}

ANALYSIS_EVERY_N_RUNS = 5
FIX_THRESHOLD = 0.6
CAPTURE_IMPROVEMENT_THRESHOLD = 0.15
DERIVE_THRESHOLD = 0.8
