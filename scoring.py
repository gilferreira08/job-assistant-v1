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


def exclusion_detected(title, description):
    txt = normalize(f"{title} {description}")
    for kw in CANDIDATE_PROFILE["excluded_role_keywords"]:
        if normalize(kw) in txt:
            return True
    return False


def title_fit_score(title):
    t = normalize(title)
    highest = CANDIDATE_PROFILE["highest_fit_roles"]
    secondary = CANDIDATE_PROFILE["secondary_fit_roles"]

    if any(normalize(r) in t for r in highest):
        return 95.0
    if any(normalize(r) in t for r in secondary):
        return 80.0
    if any(x in t for x in ["treasury", "tresorerie", "project finance", "financement de projet", "funding", "financement", "liquidity", "liquidite"]):
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

    def level_label(v):
        if v >= 85:
            return "Strong"
        if v >= 70:
            return "Good"
        if v >= 55:
            return "Moderate"
        return "Weak"

    strengths = []
    gaps = []

    if member_lens_fit >= 70:
        strengths.append("member-focus alignment")
    else:
        gaps.append("member-focus keywords")

    if jd_core_fit >= 70:
        strengths.append("core profile fit")
    else:
        gaps.append("core treasury/project-finance fit")

    if tools_fit >= 70:
        strengths.append("tools/systems match")
    else:
        gaps.append("tools/systems evidence")

    if geo_fit >= 90:
        strengths.append("excellent location fit")
    elif geo_fit < 70:
        gaps.append("location fit")

    if t_fit >= 80:
        strengths.append("title relevance")
    elif t_fit < 60:
        gaps.append("title relevance")

    short_note = (
        f"{level_label(weighted)} fit. "
        f"Strengths: {', '.join(strengths[:2]) if strengths else 'limited clear strengths'}. "
        f"Gaps: {', '.join(gaps[:2]) if gaps else 'no major gaps detected'}."
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
        "manager", "head", "director", "lead",
        "responsable", "directeur", "senior", "ownership", "pilotage"
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
