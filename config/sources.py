"""
sources.py — RSS source registry for the AI Daily Briefing system.

Defines all RSS feeds organized by tier, with section tags and crawl frequency.
"""

RSS_SOURCES = [
    # Tier 1 — primary news wires
    {
        "url": "https://news.google.com/rss/search?q=cloud+computing+AI+oracle+aws+azure&hl=en-US&gl=US&ceid=US:en",
        "name": "Google News: Cloud/AI",
        "domain": "news.google.com",
        "tier": 1,
        "credibility_score": 25,
        "sections": ["ai", "compete", "financial", "deals"],
        "crawl_freq_mins": 30,
    },
    {
        "url": "https://news.google.com/rss/search?q=datacenter+power+infrastructure&hl=en-US&gl=US&ceid=US:en",
        "name": "Google News: Datacenter/Power",
        "domain": "news.google.com",
        "tier": 1,
        "credibility_score": 25,
        "sections": ["datacenter", "power", "infrastructure"],
        "crawl_freq_mins": 30,
    },
    # Tier 2 — quality tech journalism
    {
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "name": "Ars Technica",
        "domain": "arstechnica.com",
        "tier": 2,
        "credibility_score": 20,
        "sections": ["ai", "compete", "infrastructure"],
        "crawl_freq_mins": 60,
    },
    {
        "url": "https://techcrunch.com/feed/",
        "name": "TechCrunch",
        "domain": "techcrunch.com",
        "tier": 2,
        "credibility_score": 20,
        "sections": ["ai", "deals", "compete"],
        "crawl_freq_mins": 60,
    },
    {
        "url": "https://www.wired.com/feed/rss",
        "name": "Wired",
        "domain": "wired.com",
        "tier": 2,
        "credibility_score": 20,
        "sections": ["ai", "compete"],
        "crawl_freq_mins": 60,
    },
    {
        "url": "https://www.theverge.com/rss/index.xml",
        "name": "The Verge",
        "domain": "theverge.com",
        "tier": 2,
        "credibility_score": 20,
        "sections": ["ai", "compete"],
        "crawl_freq_mins": 60,
    },
    {
        "url": "https://www.theregister.com/headlines.atom",
        "name": "The Register",
        "domain": "theregister.com",
        "tier": 2,
        "credibility_score": 20,
        "sections": ["compete", "ai", "infrastructure", "security"],
        "crawl_freq_mins": 60,
    },
    {
        "url": "https://siliconangle.com/feed/",
        "name": "SiliconAngle",
        "domain": "siliconangle.com",
        "tier": 2,
        "credibility_score": 18,
        "sections": ["ai", "compete", "deals", "financial"],
        "crawl_freq_mins": 60,
    },
    # Tier 2 — cloud/infra trade press
    {
        "url": "https://cloudwars.com/feed/",
        "name": "CloudWars",
        "domain": "cloudwars.com",
        "tier": 2,
        "credibility_score": 18,
        "sections": ["compete", "deals", "financial"],
        "crawl_freq_mins": 60,
    },
    {
        "url": "https://www.datacenterdynamics.com/en/rss/",
        "name": "DC Dynamics",
        "domain": "datacenterdynamics.com",
        "tier": 2,
        "credibility_score": 20,
        "sections": ["datacenter", "power"],
        "crawl_freq_mins": 60,
    },
    {
        "url": "https://www.technologyreview.com/feed/",
        "name": "MIT Tech Review",
        "domain": "technologyreview.com",
        "tier": 2,
        "credibility_score": 22,
        "sections": ["ai", "infrastructure", "compete"],
        "crawl_freq_mins": 60,
    },
    {
        "url": "https://www.infoq.com/feed/?token=global",
        "name": "InfoQ",
        "domain": "infoq.com",
        "tier": 2,
        "credibility_score": 18,
        "sections": ["ai", "infrastructure", "oss"],
        "crawl_freq_mins": 60,
    },
    # Tier 3 — vendor blogs
    {
        "url": "https://aws.amazon.com/blogs/aws/feed/",
        "name": "AWS Blog",
        "domain": "aws.amazon.com",
        "tier": 3,
        "credibility_score": 10,
        "sections": ["compete", "ai"],
        "crawl_freq_mins": 120,
    },
    {
        "url": "https://blogs.microsoft.com/ai/feed/",
        "name": "Microsoft AI Blog",
        "domain": "blogs.microsoft.com",
        "tier": 3,
        "credibility_score": 10,
        "sections": ["compete", "ai"],
        "crawl_freq_mins": 120,
    },
    {
        "url": "https://cloudblog.withgoogle.com/rss/",
        "name": "Google Cloud",
        "domain": "cloud.google.com",
        "tier": 3,
        "credibility_score": 10,
        "sections": ["compete", "ai"],
        "crawl_freq_mins": 120,
    },
    {
        "url": "https://news.google.com/rss/search?q=oracle+cloud+OCI&hl=en-US&gl=US&ceid=US:en",
        "name": "Oracle/OCI News",
        "domain": "news.google.com",
        "tier": 3,
        "credibility_score": 15,
        "sections": ["compete", "ai", "infrastructure"],
        "crawl_freq_mins": 120,
    },
    {
        "url": "https://openai.com/news/rss.xml",
        "name": "OpenAI Blog",
        "domain": "openai.com",
        "tier": 3,
        "credibility_score": 10,
        "sections": ["ai"],
        "crawl_freq_mins": 120,
    },
    {
        "url": "https://www.anthropic.com/rss.xml",
        "name": "Anthropic Blog",
        "domain": "anthropic.com",
        "tier": 3,
        "credibility_score": 10,
        "sections": ["ai"],
        "crawl_freq_mins": 120,
    },
    # Tier 4 — community signal
    {
        "url": "https://news.ycombinator.com/rss",
        "name": "Hacker News",
        "domain": "news.ycombinator.com",
        "tier": 4,
        "credibility_score": 5,
        "sections": ["community", "ai", "compete"],
        "crawl_freq_mins": 30,
    },
]

# Scoring constants
TIER_CREDIBILITY_SCORES = {1: 30, 2: 20, 3: 10, 4: 5}

TIMELINESS_SCORES = [
    (6,  15),   # < 6 hours
    (12, 12),   # < 12 hours
    (24, 8),    # < 24 hours
    (48, 4),    # < 48 hours
    (None, 0),  # older
]

# OCI-relevant keywords for keyword scoring bonus (max +10 pts)
OCI_KEYWORDS = {
    "oracle": 3, "oci": 3, "oracle cloud": 3,
    "aws": 2, "amazon web services": 2, "azure": 2, "microsoft cloud": 2,
    "google cloud": 2, "gcp": 2,
    "nvidia": 2, "gpu": 2, "h100": 2, "b200": 2, "a100": 2,
    "large language model": 2, "llm": 2, "generative ai": 2,
    "openai": 2, "anthropic": 2, "gemini": 2, "claude": 2, "gpt": 2,
    "foundation model": 2, "inference": 1, "training": 1,
    "datacenter": 2, "data center": 2, "colocation": 1,
    "power grid": 2, "megawatt": 2, "gigawatt": 2, "nuclear": 2,
    "hyperscaler": 2, "sovereign cloud": 2,
    "cloud deal": 2, "enterprise contract": 2, "partnership": 1, "acquisition": 2,
    "ipo": 1, "earnings": 2, "valuation": 1,
    "zero trust": 1, "security breach": 2, "ransomware": 2, "kubernetes": 1,
    "open source": 1, "developer platform": 1,
}

MAX_KEYWORD_BONUS = 10

# Section keyword mapping for supplemental tagging
SECTION_KEYWORDS: dict[str, list[str]] = {
    "ai":           ["artificial intelligence", "machine learning", "llm", "neural", "gpt",
                     "claude", "gemini", "openai", "anthropic", "generative", "deep learning",
                     "foundation model", "large language", "inference", "gpu", "nvidia"],
    "financial":    ["earnings", "revenue", "profit", "ipo", "valuation", "stock", "quarterly",
                     "fiscal", "billion", "million", "forecast", "guidance"],
    "compete":      ["aws", "amazon web services", "azure", "google cloud", "gcp", "microsoft",
                     "alibaba cloud", "ibm cloud", "competitor", "market share", "beats"],
    "datacenter":   ["datacenter", "data center", "colocation", "colo", "facility", "campus",
                     "rack", "cooling", "pue"],
    "power":        ["megawatt", "gigawatt", "mw", "gw", "power grid", "energy", "electricity",
                     "nuclear", "solar", "renewable", "utility"],
    "deals":        ["acquisition", "merger", "deal", "contract", "agreement", "partnership",
                     "signed", "awarded", "procurement"],
    "security":     ["security", "breach", "vulnerability", "cve", "ransomware", "zero trust",
                     "soc2", "fedramp", "compliance", "audit"],
    "multicloud":   ["multicloud", "multi-cloud", "hybrid cloud", "cloud-agnostic", "portability"],
    "oss":          ["open source", "open-source", "github", "linux", "apache", "kubernetes",
                     "helm", "terraform", "pytorch", "hugging face"],
    "partnerships": ["partnership", "collaborate", "integrate", "ecosystem", "isv", "gsi"],
    "community":    ["hacker news", "reddit", "developer", "community", "forum", "discussion"],
    "infrastructure": ["infrastructure", "networking", "storage", "compute", "vpc", "cdn"],
}
