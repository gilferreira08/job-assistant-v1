import re
import unicodedata

from knowledge import BOARD_MEMBERS, BOARD_KEYWORDS
from candidate_profile import CANDIDATE_PROFILE


def clamp(value):
    return max(0.0, min(100.0, float(value)))


def strip_accents(text):
    text = text or ""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def normalize(text):
    text = strip_accents(text)
    return re.sub(r"\s+", " ", text.lower()).strip()


def keyword_hit_score(text, keywords):
    txt = normalize(text)
    if not keywords:
        return 0.0

    hits = sum(1 for kw in keywords if normalize(kw) in txt)
    ratio = hits / len(keywords)

    if hits == 0:
        return 10.0
    if ratio >= 0.60:
        return 95.0
    if ratio >= 0.40:
        return 85.0
    if ratio >= 0.25:
        return 75.0
    if ratio >= 0.15:
        return 65.0
    return 50.0


def get_exclusion_keywords():
    """
    Safer exclusion list for regex word-boundary detection.
    Avoid ultra-short ambiguous tokens like 'ap'/'ar' alone.
    """
    return [
        "accounting",
        "comptabilite",
        "audit",
        "intern",
        "internship",
        "stage",
        "graduate",
        "junior",
        "debutant",
        "alternance",
        "tax",
        "fiscalite",
        "back office",
        "back-office",
        "compliance",
        "pure reporting",
        "reporting uniquement",
        "ap/ar",
        "accounts payable",
        "accounts receivable",
    ]


def exclusion_reason(title, description):
    txt = normalize(f"{title} {description}")
    for kw in get_exclusion_keywords():
        pattern = r"\b" + re.escape(normalize(kw)) + r"\b"
        if re.search(pattern, txt):
            return f"automatic exclusion keyword match: {kw}"
    return ""


def exclusion_detected(title, description):
    return exclusion_reason(title, description) != ""


def title_fit_score(title):
    t = normalize(title)
    highest = CANDIDATE_PROFILE["highest_fit_roles"]
    secondary = CANDIDATE_PROFILE["secondary_fit_roles"]

    if any(normalize(r) in t for r in highest):
        return 95.0
    if any(normalize(r) in t for r in secondary):
        return 80.0

    if any(
        x in t for x in [
            "treasury", "tresorerie",
            "project finance", "financement de projet",
            "funding", "financement",
            "liquidity", "liquidite",
            "structured finance", "finance structuree"
        ]
    ):
        return 70.0

    return 45.0


def location_fit_score(country):
    c = normalize(country)
    targets = [normalize(x) for x in CANDIDATE_PROFILE["target_geographies"]]

    if c in targets:
        if c in ["france", "portugal", "switzerland", "suisse"]:
            return 100.0
        if c in ["remote europe", "europe remote", "teletravail europe", "remote"]:
            return 95.0
        if c in ["brazil", "bresil"]:
            return 90.0
        if c == "luxembourg":
            return 85.0
        return 80.0

    return 50.0


def weighted_technical_score(
    treasury_hedging_score,
    project_finance_score,
    debt_funding_score,
    seniority_score,
    tools_systems_score,
    location_score,
):
    treasury_hedging_score = clamp(treasury_hedging_score)
    project_finance_score = clamp(project_finance_score)
    debt_funding_score = clamp(debt_funding_score)
    seniority_score = clamp(seniority_score)
    tools_systems_score = clamp(tools_systems_score)
    location_score = clamp(location_score)

    core_max = max(treasury_hedging_score, project_finance_score, debt_funding_score)

    return (
        (core_max * 0.60)
        + (seniority_score * 0.15)
        + (tools_systems_score * 0.15)
        + (location_score * 0.10)
    )


def final_score(weighted_technical, board_average):
    return (clamp(weighted_technical) * 0.65) + (clamp(board_average) * 0.35)


def recommendation(score, verified_active=True, excluded=False):
    score = clamp(score)
    if excluded or not verified_active:
        return "Skip"
    if score >= 80:
        return "Apply Now"
    if score >= 70:
        return "Consider"
    return "Skip"


def priority(score, excluded=False):
    score = clamp(score)
    if excluded:
        return "Excluded"
    if score >= 88:
        return "Very High"
    if score >= 80:
        return "High"
    if score >= 70:
        return "Medium"
    return "Low"


def board_member_note(member, member_lens_fit, jd_core_fit, tools_fit, t_fit, geo_fit):
    def label(v):
        if v >= 85:
            return "strong"
        if v >= 70:
            return "good"
        if v >= 55:
            return "moderate"
        return "weak"

    if member == "HR Director":
        strengths, gaps = [], []
        if member_lens_fit >= 70:
            strengths.append("communication/stakeholder profile")
        if geo_fit >= 90:
            strengths.append("international/location alignment")
        if t_fit >= 75:
            strengths.append("seniority/title coherence")
        if member_lens_fit < 60:
            gaps.append("people leadership evidence")
        if t_fit < 60:
            gaps.append("role seniority signal")
        if geo_fit < 70:
            gaps.append("mobility/location fit")
        action = "Emphasize leadership, cross-functional collaboration, and language fluency."

    elif member == "CFO":
        strengths, gaps = [], []
        if jd_core_fit >= 75:
            strengths.append("strategic finance relevance")
        if member_lens_fit >= 70:
            strengths.append("funding/capital structure exposure")
        if t_fit >= 75:
            strengths.append("decision-level role positioning")
        if jd_core_fit < 60:
            gaps.append("business impact clarity")
        if member_lens_fit < 60:
            gaps.append("capital structure/funding depth")
        if geo_fit < 70:
            gaps.append("market fit")
        action = "Highlight value creation, financing strategy, and executive impact."

    elif member == "Head of Treasury":
        strengths, gaps = [], []
        if jd_core_fit >= 75:
            strengths.append("treasury core alignment")
        if member_lens_fit >= 70:
            strengths.append("liquidity/funding/hedging fit")
        if tools_fit >= 70:
            strengths.append("TMS/tools capability")
        if member_lens_fit < 60:
            gaps.append("treasury ownership scope")
        if tools_fit < 60:
            gaps.append("systems/automation depth")
        action = "Stress treasury ownership, liquidity governance, and hedging sophistication."

    elif member == "Hiring Manager":
        strengths, gaps = [], []
        if member_lens_fit >= 70:
            strengths.append("execution readiness")
        if jd_core_fit >= 70:
            strengths.append("problem-solving fit")
        if t_fit >= 70:
            strengths.append("role seniority alignment")
        if member_lens_fit < 60:
            gaps.append("hands-on delivery evidence")
        if jd_core_fit < 60:
            gaps.append("immediate operational impact")
        action = "Demonstrate quick-win delivery and practical implementation capacity."

    elif member == "FP&A Manager":
        strengths, gaps = [], []
        if member_lens_fit >= 70:
            strengths.append("forecasting/scenario fit")
        if jd_core_fit >= 70:
            strengths.append("analytical rigor")
        if tools_fit >= 70:
            strengths.append("modeling/tools readiness")
        if member_lens_fit < 60:
            gaps.append("planning/scenario depth")
        if tools_fit < 60:
            gaps.append("modeling tooling evidence")
        action = "Show DSCR/IRR/CFADS and scenario-analysis impact."

    elif member == "Financial Risk Manager":
        strengths, gaps = [], []
        if member_lens_fit >= 70:
            strengths.append("risk/hedging relevance")
        if jd_core_fit >= 70:
            strengths.append("exposure management fit")
        if tools_fit >= 70:
            strengths.append("risk analytics tooling")
        if member_lens_fit < 60:
            gaps.append("derivatives/risk framework detail")
        if jd_core_fit < 60:
            gaps.append("risk governance ownership")
        action = "Highlight FX/IR hedging strategy and risk governance outcomes."

    else:  # Project Finance Director
        strengths, gaps = [], []
        if member_lens_fit >= 70:
            strengths.append("project finance technical fit")
        if jd_core_fit >= 70:
            strengths.append("structuring/refinancing relevance")
        if t_fit >= 70:
            strengths.append("senior mandate alignment")
        if member_lens_fit < 60:
            gaps.append("DSCR/IRR/CFADS evidence")
        if jd_core_fit < 60:
            gaps.append("infrastructure financing depth")
        action = "Emphasize debt sizing, bankability, and long-term financing strategy."

    strengths_txt = ", ".join(strengths[:2]) if strengths else "limited clear strengths"
    gaps_txt = ", ".join(gaps[:2]) if gaps else "no major gaps detected"

    avg_signal = (member_lens_fit + jd_core_fit + tools_fit + t_fit + geo_fit) / 5
    overall = label(avg_signal).capitalize()

    return f"{overall} fit. Strengths: {strengths_txt}. Gaps: {gaps_txt}. Action: {action}"


def board_member_score(member, title, description, country):
    jd_core_fit = keyword_hit_score(description, CANDIDATE_PROFILE["core_strength_keywords"])
    member_lens_fit = keyword_hit_score(description, BOARD_KEYWORDS.get(member, []))
    tools_fit = keyword_hit_score(description, CANDIDATE_PROFILE["tools_keywords"])
    t_fit = title_fit_score(title)
    geo_fit = location_fit_score(country)

    if member == "HR Director":
        raw = (member_lens_fit * 0.40) + (jd_core_fit * 0.25) + (t_fit * 0.15) + (geo_fit * 0.20)
    elif member == "CFO":
        raw = (member_lens_fit * 0.25) + (jd_core_fit * 0.50) + (t_fit * 0.15) + (geo_fit * 0.10)
    elif member == "Head of Treasury":
        raw = (member_lens_fit * 0.30) + (jd_core_fit * 0.45) + (tools_fit * 0.15) + (t_fit * 0.10)
    elif member == "Hiring Manager":
        raw = (member_lens_fit * 0.30) + (jd_core_fit * 0.40) + (t_fit * 0.20) + (tools_fit * 0.10)
    elif member == "FP&A Manager":
        raw = (member_lens_fit * 0.30) + (jd_core_fit * 0.35) + (tools_fit * 0.25) + (t_fit * 0.10)
    elif member == "Financial Risk Manager":
        raw = (member_lens_fit * 0.35) + (jd_core_fit * 0.40) + (t_fit * 0.10) + (tools_fit * 0.15)
    elif member == "Project Finance Director":
        raw = (member_lens_fit * 0.30) + (jd_core_fit * 0.45) + (t_fit * 0.10) + (geo_fit * 0.15)
    else:
        raw = (member_lens_fit * 0.35) + (jd_core_fit * 0.35) + (t_fit * 0.20) + (geo_fit * 0.10)

    raw = clamp(raw)
    weighted = clamp((raw * 0.95) + (t_fit * 0.05))

    short_note = board_member_note(
        member=member,
        member_lens_fit=member_lens_fit,
        jd_core_fit=jd_core_fit,
        tools_fit=tools_fit,
        t_fit=t_fit,
        geo_fit=geo_fit,
    )

    reason = (
        f"lens={member_lens_fit:.1f}, core={jd_core_fit:.1f}, "
        f"title={t_fit:.1f}, geo={geo_fit:.1f}, tools={tools_fit:.1f}"
    )

    return {
        "description_score": round(raw, 2),
        "title_score": round(t_fit, 2),
        "weighted_score": round(weighted, 2),
        "reason": reason,
        "short_note": short_note,
    }


def compute_board_scores(title, description, country):
    scores = {}
    for member in BOARD_MEMBERS:
        scores[member] = board_member_score(member, title, description, country)

    board_avg = round(sum(v["weighted_score"] for v in scores.values()) / len(scores), 2)
    return scores, board_avg


def auto_technical_suggestion(title, description, country):
    treasury_keywords = [
        "treasury", "tresorerie", "liquidity", "liquidite", "cash forecasting",
        "prevision de tresorerie", "hedging", "couverture", "fx", "change"
    ]
    project_fin_keywords = [
        "project finance", "financement de projet", "infrastructure", "dscr", "irr", "tri", "cfads",
        "bankability", "bancabilite"
    ]
    debt_funding_keywords = [
        "funding", "financement", "debt", "dette", "refinancing", "refinancement",
        "capital structure", "structure du capital"
    ]
    seniority_keywords = [
        "manager", "head", "director", "lead", "responsable", "directeur", "senior", "ownership", "pilotage"
    ]

    treasury_score = keyword_hit_score(description, treasury_keywords)
    project_fin_score = keyword_hit_score(description, project_fin_keywords)
    debt_funding_score = keyword_hit_score(description, debt_funding_keywords)
    tools_score = keyword_hit_score(description, CANDIDATE_PROFILE["tools_keywords"])
    t_fit = title_fit_score(title)
    geo_fit = location_fit_score(country)

    seniority_from_jd = keyword_hit_score(f"{title} {description}", seniority_keywords)
    seniority_score = clamp((seniority_from_jd * 0.6) + (t_fit * 0.4))

    auto_weighted = weighted_technical_score(
        treasury_score,
        project_fin_score,
        debt_funding_score,
        seniority_score,
        tools_score,
        geo_fit,
    )

    return {
        "treasury_hedging": round(treasury_score, 2),
        "project_finance": round(project_fin_score, 2),
        "debt_funding": round(debt_funding_score, 2),
        "seniority": round(seniority_score, 2),
        "tools_systems": round(tools_score, 2),
        "location_fit": round(geo_fit, 2),
        "weighted_technical_score": round(auto_weighted, 2),
    }
