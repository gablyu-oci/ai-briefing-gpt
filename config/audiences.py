"""
audiences.py — Audience profile definitions for OCI executives.

Each profile defines section weights, tone guidance, and display metadata.
"""

AUDIENCE_PROFILES = {
    "karan": {
        "id": "karan",
        "name": "Karan Batta",
        "title": "SVP, Product",
        "email": "karan@example.com",
        "tone": "concise, high signal, strategic",
        "tone_guidance": (
            "Be concise and strategic. Lead with the bottom line. "
            "Maximum 20 words per executive summary bullet. "
            "One crisp sentence per non-hero story summary. "
            "Highlight financial impact, competitive positioning, and deal signals. "
            "Use plain language — no financial jargon (avoid: 'bear thesis,' 'sentiment shift,' 'beachhead'). "
            "Target total briefing read time under 90 seconds."
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
            "Highlight how OCI can expand into adjacent platform opportunities. "
            "Use action-oriented framing: 'OCI should evaluate...' not 'For OCI, this validates...' "
            "Name specific ISVs, GSIs, and portfolio companies — avoid vague references like 'peers' or 'potential partners.' "
            "Note ISV, GSI, and hyperscaler partnership angles with concrete next steps."
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
            "Prioritize technical depth over strategic framing. "
            "Lead AI stories with architecture, model size, benchmark scores, and inference metrics. "
            "Include specific numbers: parameter counts, tokens/sec, latency, pricing. "
            "Cover open-source ecosystem moves, competitive AI/data platform developments, and model releases. "
            "Never use MBA jargon ('escape velocity,' 'commands premium multiples'). "
            "Be direct about implications for OCI's AI and data strategy with technical specifics."
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
            "and developer platform signals. Highlight OCI's resilience and sovereign-cloud angles. "
            "Note regulatory, compliance, and supply-chain risks with specific frameworks "
            "(FedRAMP, EU AI Act, DISA IL, data residency requirements). "
            "Flag security vulnerabilities with CVE numbers and severity ratings. "
            "Prioritize stories that affect OCI's security certification posture."
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
