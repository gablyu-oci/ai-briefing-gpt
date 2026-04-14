"""
config.py — Audience profiles, RSS sources, and scoring weights
for the OCI AI Daily Executive Briefing System.
"""

from config.settings import (
    INGEST_WINDOW_HOURS,
    MAX_ARTICLES_TO_CLASSIFY,
    MAX_CONCURRENT_LLM,
    TOP_ARTICLES_PER_AUDIENCE,
)

# ---------------------------------------------------------------------------
# Audience Profiles
# ---------------------------------------------------------------------------
# Each profile defines section weights (must sum to 1.0), tone guidance,
# and a display name used in rendering.

AUDIENCE_PROFILES = {
    "karan": {
        "id": "karan",
        "name": "Karan Batta",
        "title": "SVP, Product",
        "email": "karan@example.com",
        "tone": "concise, high signal, strategic",
        "tone_guidance": (
            "Be concise and strategic. Lead with the bottom line. "
            "Highlight financial impact, competitive positioning, and deal signals. "
            "Avoid jargon. One crisp insight per item."
        ),
        "section_weights": {
            "financial": 0.35,
            "compete":   0.25,
            "datacenter": 0.15,
            "ai":        0.15,
            "deals":     0.10,
        },
        "accent_color": "#C74634",
    },
    "nathan": {
        "id": "nathan",
        "name": "Nathan Thomas",
        "title": "SVP, Product",
        "email": "nathan@example.com",
        "tone": "ecosystem, partner-aware",
        "tone_guidance": (
            "Focus on multi-cloud dynamics, partner ecosystem shifts, and deal flow. "
            "Highlight emerging platform opportunities and competitive positioning. "
            "Note ISV, GSI, and hyperscaler partnership angles."
        ),
        "section_weights": {
            "multicloud":    0.30,
            "ai":            0.25,
            "deals":         0.25,
            "compete":       0.10,
            "financial":     0.10,
        },
        "accent_color": "#1B6EC2",
    },
    "greg": {
        "id": "greg",
        "name": "Greg Pavlik",
        "title": "EVP, Data & AI",
        "email": "greg@example.com",
        "tone": "technical executive",
        "tone_guidance": (
            "Prioritize technical depth. Cover model benchmarks, infrastructure advances, "
            "open-source ecosystem moves, and competitive AI/data platform developments. "
            "Be direct about strategic implications for AI and data infrastructure."
        ),
        "section_weights": {
            "compete":      0.35,
            "ai":           0.35,
            "oss":          0.15,
            "partnerships": 0.10,
            "community":    0.05,
        },
        "accent_color": "#2E7D32",
    },
    "mahesh": {
        "id": "mahesh",
        "name": "Mahesh Thiagarajan",
        "title": "EVP, Security & Developer Platform",
        "email": "mahesh@example.com",
        "tone": "platform, resilience, scale",
        "tone_guidance": (
            "Focus on infrastructure scale, power/energy constraints, security posture, "
            "and developer platform signals. Highlight resilience and sovereign-cloud angles. "
            "Note regulatory, compliance, and supply-chain risks."
        ),
        "section_weights": {
            "datacenter": 0.25,
            "power":      0.20,
            "ai":         0.20,
            "deals":      0.20,
            "security":   0.15,
        },
        "accent_color": "#6A1B9A",
    },
}

AUDIENCE_ORDER = ["karan", "nathan", "greg", "mahesh"]

# ---------------------------------------------------------------------------
# RSS Sources
# ---------------------------------------------------------------------------
RSS_SOURCES = [
    # Tier 1 — wire services & business news
    {"url": "https://news.google.com/rss/search?q=site:reuters.com+technology&hl=en-US&gl=US&ceid=US:en", "name": "Reuters Tech", "tier": 1, "sections": ["financial", "compete", "deals"]},
    {"url": "https://news.google.com/rss/search?q=site:reuters.com+business+technology&hl=en-US&gl=US&ceid=US:en", "name": "Reuters Business", "tier": 1, "sections": ["financial", "deals"]},
    {"url": "https://feeds.bloomberg.com/technology/news.rss",   "name": "Bloomberg Tech",   "tier": 1, "sections": ["financial", "compete", "deals"]},
    {"url": "https://feeds.content.dowjones.io/public/rss/RSSWSJD", "name": "WSJ Tech",     "tier": 1, "sections": ["financial", "compete", "deals"]},
    {"url": "https://www.ft.com/technology?format=rss",          "name": "Financial Times",  "tier": 1, "sections": ["financial", "compete", "deals"]},
    {"url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910", "name": "CNBC Tech", "tier": 1, "sections": ["financial", "compete", "deals"]},
    # Tier 2 — quality tech journalism
    {"url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "name": "Ars Technica", "tier": 2, "sections": ["ai", "compete", "infrastructure"]},
    {"url": "https://techcrunch.com/feed/",                     "name": "TechCrunch",       "tier": 2, "sections": ["ai", "deals", "compete"]},
    {"url": "https://venturebeat.com/category/ai/feed/",        "name": "VentureBeat AI",   "tier": 2, "sections": ["ai", "compete"]},
    # Tier 2 — cloud/infra trade press
    {"url": "https://cloudwars.com/feed/",                      "name": "CloudWars",        "tier": 2, "sections": ["compete", "deals", "financial"]},
    {"url": "https://www.datacenterdynamics.com/en/rss/",       "name": "DC Dynamics",      "tier": 2, "sections": ["datacenter", "power"]},
    {"url": "https://thenewstack.io/blog/feed/",                "name": "The New Stack",    "tier": 2, "sections": ["infrastructure", "oss", "ai"]},
    {"url": "https://www.lightreading.com/rss.xml",             "name": "Light Reading",    "tier": 2, "sections": ["infrastructure", "datacenter"]},
    # Tier 2 — AI-focused
    {"url": "https://newsletter.semianalysis.com/feed",         "name": "SemiAnalysis",     "tier": 2, "sections": ["ai", "datacenter", "compete"]},
    {"url": "https://importai.substack.com/feed",               "name": "Import AI",        "tier": 2, "sections": ["ai", "compete"]},
    # Tier 2 — security
    {"url": "https://krebsonsecurity.com/feed/",                "name": "KrebsOnSecurity",  "tier": 2, "sections": ["security"]},
    {"url": "https://therecord.media/feed/",                    "name": "The Record",       "tier": 2, "sections": ["security", "compete"]},
    # Tier 3 — vendor blogs
    {"url": "https://aws.amazon.com/blogs/aws/feed/",           "name": "AWS Blog",         "tier": 3, "sections": ["compete", "ai"]},
    {"url": "https://azure.microsoft.com/en-us/blog/feed/",     "name": "Azure Blog",       "tier": 3, "sections": ["compete", "ai"]},
    {"url": "https://cloudblog.withgoogle.com/rss/",              "name": "Google Cloud",     "tier": 3, "sections": ["compete", "ai"]},
    {"url": "https://news.google.com/rss/search?q=site:blogs.oracle.com+cloud&hl=en-US&gl=US&ceid=US:en", "name": "OCI Blog", "tier": 3, "sections": ["compete", "ai"]},
    {"url": "https://openai.com/news/rss.xml",                  "name": "OpenAI Blog",      "tier": 3, "sections": ["ai"]},
    {"url": "https://news.google.com/rss/search?q=site:anthropic.com&hl=en-US&gl=US&ceid=US:en", "name": "Anthropic Blog", "tier": 3, "sections": ["ai"]},
    {"url": "https://deepmind.google/blog/rss.xml",             "name": "DeepMind Blog",    "tier": 3, "sections": ["ai", "compete"]},
    {"url": "https://huggingface.co/blog/feed.xml",             "name": "Hugging Face",     "tier": 3, "sections": ["ai", "oss"]},
    # CNCF removed — feed returns 403
    # Tier 4 — community signal
    {"url": "https://news.ycombinator.com/rss",                 "name": "Hacker News",      "tier": 4, "sections": ["community", "ai", "compete"]},
    # Tier 4 — Reddit community signal
    {"url": "https://www.reddit.com/r/cloudcomputing/.rss", "name": "r/cloudcomputing", "tier": 4, "sections": ["compete", "infrastructure"]},
    {"url": "https://www.reddit.com/r/aws/.rss", "name": "r/aws", "tier": 4, "sections": ["compete", "infrastructure"]},
    {"url": "https://www.reddit.com/r/kubernetes/.rss", "name": "r/kubernetes", "tier": 4, "sections": ["infrastructure", "oss"]},
    {"url": "https://www.reddit.com/r/artificial/.rss", "name": "r/artificial", "tier": 4, "sections": ["ai", "compete"]},
    {"url": "https://www.reddit.com/r/MachineLearning/.rss", "name": "r/MachineLearning", "tier": 4, "sections": ["ai"]},
]

# ---------------------------------------------------------------------------
# Scoring Weights
# ---------------------------------------------------------------------------
TIER_CREDIBILITY_SCORES = {
    1: 30,
    2: 20,
    3: 10,
    4: 5,
}

TIMELINESS_SCORES = [
    (6,  15),   # < 6 hours
    (12, 12),   # < 12 hours
    (24, 8),    # < 24 hours
    (48, 4),    # < 48 hours
    (None, 0),  # older
]

# Keywords for scoring bonus (max +10 pts)
OCI_KEYWORDS = {
    # Hyperscaler competitors
    "aws": 2, "amazon web services": 2, "azure": 2, "microsoft cloud": 2,
    "google cloud": 2, "gcp": 2,
    # AI / ML
    "nvidia": 2, "gpu": 2, "h100": 2, "b200": 2, "a100": 2,
    "large language model": 2, "llm": 2, "generative ai": 2,
    "openai": 2, "anthropic": 2, "gemini": 2, "claude": 2, "gpt": 2,
    "foundation model": 2, "inference": 1, "training": 1,
    # Infrastructure
    "datacenter": 2, "data center": 2, "colocation": 1,
    "power grid": 2, "megawatt": 2, "gigawatt": 2, "nuclear": 2,
    "hyperscaler": 2, "sovereign cloud": 2,
    # Business signals
    "cloud deal": 2, "enterprise contract": 2, "partnership": 1, "acquisition": 2,
    "ipo": 2, "earnings": 2, "valuation": 1, "revenue": 2, "run rate": 2,
    "custom silicon": 2, "custom chip": 2,
    # Security / Dev
    "zero trust": 1, "security breach": 2, "ransomware": 2, "kubernetes": 1,
    "open source": 1, "developer platform": 1,
}

# Maximum keyword bonus
MAX_KEYWORD_BONUS = 10

# Pipeline settings are shared with config.settings so CLI env overrides apply
# consistently across the project.
