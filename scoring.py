def clamp(value):
    return max(0, min(100, float(value)))

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
