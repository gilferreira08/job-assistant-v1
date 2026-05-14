def auto_technical_suggestion(title, description, country):
    """
    Lightweight automatic technical suggestion from JD/title/country.
    Returns component scores + weighted technical score.
    """
    jd_core_fit = keyword_hit_score(description, CANDIDATE_PROFILE["core_strength_keywords"])
    tools_fit = keyword_hit_score(description, CANDIDATE_PROFILE["tools_keywords"])
    t_fit = title_fit_score(title)
    geo_fit = location_fit_score(country)

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

    treasury_score = keyword_hit_score(description, treasury_keywords)
    project_fin_score = keyword_hit_score(description, project_fin_keywords)
    debt_funding_score = keyword_hit_score(description, debt_funding_keywords)

    seniority_keywords = ["manager", "head", "director", "lead", "responsable", "directeur", "senior", "ownership"]
    seniority_from_jd = keyword_hit_score(f"{title} {description}", seniority_keywords)
    seniority_score = clamp((seniority_from_jd * 0.6) + (t_fit * 0.4))

    tools_score = tools_fit
    location_score = geo_fit

    auto_weighted = weighted_technical_score(
        treasury_score,
        project_fin_score,
        debt_funding_score,
        seniority_score,
        tools_score,
        location_score,
    )

    return {
        "treasury_hedging": round(treasury_score, 2),
        "project_finance": round(project_fin_score, 2),
        "debt_funding": round(debt_funding_score, 2),
        "seniority": round(seniority_score, 2),
        "tools_systems": round(tools_score, 2),
        "location_fit": round(location_score, 2),
        "weighted_technical_score": round(auto_weighted, 2),
    }
