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
    """
    Calibrated keyword score:
    - Avoids very low scores when a JD is relevant but wording differs.
    - Still rewards richer keyword coverage.
    """
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
    weighted_technical = clamp(weighted_technical)
    board_average = clamp(board_average)
    return (weighted_technical * 0.65) + (board_average * 0.35)


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
    """
    Profile-aware board score by member.

    95/5 rule is kept:
    weighted = raw_description_view * 0.95 + title_fit * 0.05
    """
    jd_core_fit = keyword_hit_score(description, CANDIDATE_PROFILE["core_strength_keywords"])
    member_lens_fit = keyword_hit_score(description, BOARD_KEYWORDS.get(member, []))
    tools_fit = keyword_hit_score(description, CANDIDATE_PROFILE["tools_keywords"])
    t_fit = title_fit_score(title)
    geo_fit = location_fit_score(country)

    # Calibrated member logic: stronger weight on core JD-profile fit
    if member == "HR Director":
        raw = (
            (member_lens_fit * 0.40)
            + (jd_core_fit * 0.25)
            + (t_fit * 0.15)
            + (geo_fit * 0.20)
        )
    elif member == "CFO":
        raw = (
            (member_lens_fit * 0.25)
            + (jd_core_fit * 0.50)
            + (t_fit * 0.15)
            + (geo_fit * 0.10)
        )
    elif member == "Head of Treasury":
        raw = (
            (member_lens_fit * 0.30)
            + (jd_core_fit * 0.45)
            + (tools_fit * 0.15)
            + (t_fit * 0.10)
        )
    elif member == "Hiring Manager":
        raw = (
            (member_lens_fit * 0.30)
            + (jd_core_fit * 0.40)
            + (t_fit * 0.20)
            + (tools_fit * 0.10)
        )
    elif member == "FP&A Manager":
        raw = (
            (member_lens_fit * 0.30)
            + (jd_core_fit * 0.35)
            + (tools_fit * 0.25)
            + (t_fit * 0.10)
        )
    elif member == "Financial Risk Manager":
        raw = (
            (member_lens_fit * 0.35)
            + (jd_core_fit * 0.40)
            + (t_fit * 0.10)
            + (tools_fit * 0.15)
        )
    elif member == "Project Finance Director":
        raw = (
            (member_lens_fit * 0.30)
            + (jd_core_fit * 0.45)
            + (t_fit * 0.10)
            + (geo_fit * 0.15)
        )
    else:
        raw = (
            (member_lens_fit * 0.35)
            + (jd_core_fit * 0.35)
            + (t_fit * 0.20)
            + (geo_fit * 0.10)
        )

    raw = clamp(raw)
    weighted = clamp((raw * 0.95) + (t_fit * 0.05))

    reason = (
        f"{member}: lens={member_lens_fit:.1f}, core_fit={jd_core_fit:.1f}, "
        f"title_fit={t_fit:.1f}, geo_fit={geo_fit:.1f}, tools_fit={tools_fit:.1f}"
    )

    return {
        "description_score": round(raw, 2),
        "title_score": round(t_fit, 2),
        "weighted_score": round(weighted, 2),
        "reason": reason,
    }


def compute_board_scores(title, description, country):
    scores = {}
    for member in BOARD_MEMBERS:
        scores[member] = board_member_score(member, title, description, country)

    board_avg = round(sum(v["weighted_score"] for v in scores.values()) / len(scores), 2)
    return scores, board_avg
