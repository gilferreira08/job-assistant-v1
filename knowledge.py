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
    "accounting", "comptabilite",
    "audit",
    "ap", "ar",
    "intern", "internship", "stage",
    "graduate", "junior", "debutant", "alternance",
    "tax", "fiscalite",
    "back office", "back-office",
    "compliance",
    "pure reporting", "reporting uniquement",
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

BOARD_KEYWORDS = {
    "HR Director": [
        "leadership", "management", "communication", "stakeholder",
        "cross-functional", "team", "international", "culture",
        "leadership", "communication", "parties prenantes",
        "transverse", "equipe", "international", "culture"
    ],
    "CFO": [
        "strategic", "capital structure", "funding", "refinancing",
        "liquidity", "cash flow", "value creation", "governance",
        "strategie", "structure du capital", "financement", "refinancement",
        "liquidite", "flux de tresorerie", "creation de valeur", "gouvernance"
    ],
    "Head of Treasury": [
        "treasury", "cash management", "liquidity", "funding", "hedging",
        "fx", "interest rate", "tms", "treasury transformation",
        "tresorerie", "gestion de tresorerie", "liquidite", "financement",
        "couverture", "taux d'interet", "transformation tresorerie"
    ],
    "Hiring Manager": [
        "execution", "delivery", "ownership", "implementation",
        "problem solving", "hands-on", "operations",
        "execution", "livraison", "responsabilite", "mise en oeuvre",
        "resolution de problemes", "operationnel"
    ],
    "FP&A Manager": [
        "forecast", "budget", "scenario", "analysis", "kpi",
        "financial modelling", "variance", "planning", "reporting",
        "prevision", "budget", "scenario", "analyse", "kpi",
        "modelisation financiere", "ecarts", "planification", "reporting"
    ],
    "Financial Risk Manager": [
        "risk", "derivatives", "fx", "interest rate", "hedging",
        "exposure", "sensitivity", "var", "stress testing",
        "risque", "derives", "change", "taux", "couverture",
        "exposition", "sensibilite", "stress test"
    ],
    "Project Finance Director": [
        "project finance", "infrastructure", "dscr", "irr", "cfads",
        "debt sizing", "bankability", "refinancing", "long-term financing",
        "financement de projet", "infrastructure", "dscr", "tri", "cfads",
        "dimensionnement de la dette", "bancabilite", "refinancement", "financement long terme"
    ],
}
