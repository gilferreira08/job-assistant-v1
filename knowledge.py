TARGET_GEOS = [
    "France",
    "Portugal",
    "Switzerland",
    "Luxembourg",
    "Brazil",
    "Remote Europe",
    "Other",
]

EXCLUDED_KEYWORDS = [
    "accounting",
    "audit",
    "ap",
    "ar",
    "intern",
    "graduate",
    "junior",
    "tax",
    "back office",
    "compliance",
    "pure reporting",
]

BOARD_MEMBERS = [
    "HR Director",
    "CFO",
    "Head of Treasury",
    "Hiring Manager",
    "FP&A Manager",
    "Financial Risk Manager",
    "Project Finance Director",
]

# Lightweight board "lens" keywords per member
BOARD_KEYWORDS = {
    "HR Director": [
        "leadership", "stakeholder", "communication", "collaboration",
        "international", "cross-functional", "team", "english", "french"
    ],
    "CFO": [
        "strategic", "capital structure", "funding", "refinancing",
        "liquidity", "cash flow", "value creation", "governance"
    ],
    "Head of Treasury": [
        "treasury", "liquidity", "cash management", "funding",
        "hedging", "fx", "interest rate", "tms", "treasury transformation"
    ],
    "Hiring Manager": [
        "execution", "delivery", "ownership", "implementation",
        "problem solving", "hands-on", "operations"
    ],
    "FP&A Manager": [
        "forecast", "budget", "scenario", "analysis", "kpi",
        "financial modelling", "variance", "planning", "reporting"
    ],
    "Financial Risk Manager": [
        "risk", "derivatives", "fx", "interest rate", "hedging",
        "exposure", "sensitivity", "var", "stress testing"
    ],
    "Project Finance Director": [
        "project finance", "infrastructure", "dscr", "irr", "cfads",
        "debt sizing", "bankability", "refinancing", "long-term financing"
    ],
}
