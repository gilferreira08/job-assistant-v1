import streamlit as st
import pandas as pd

from knowledge import TARGET_GEOS, BOARD_MEMBERS
from scoring import (
    weighted_technical_score,
    final_score,
    recommendation,
    priority,
    compute_board_scores,
    exclusion_detected,
)
from storage import init_db, load_jobs, save_job, exists_duplicate

st.set_page_config(page_title="Treasury Job Assistant", layout="wide")
st.title("Treasury / Project Finance Job Assistant (Lean MVP)")
st.caption("Paste job info (EN or FR), then click Run Analysis.")

init_db()
if "jobs" not in st.session_state:
    st.session_state.jobs = load_jobs()

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

st.subheader("Add Job")

with st.form("job_form"):
    col1, col2 = st.columns(2)

    with col1:
        company = st.text_input("Company")
        position = st.text_input("Position")
        location = st.text_input("Location")
        country = st.selectbox("Country", TARGET_GEOS)
        source = st.text_input("Source")
        application_link = st.text_input("Application Link")
        job_description = st.text_area("Job Description (required, EN or FR)", height=220)

    with col2:
        treasury_hedging = st.slider("Treasury / Hedging Score", 0, 100, 70)
        project_finance = st.slider("Project Finance Score", 0, 100, 70)
        debt_funding = st.slider("Debt / Funding Score", 0, 100, 70)
        seniority = st.slider("Seniority Score", 0, 100, 70)
        tools_systems = st.slider("Tools & Systems Score", 0, 100, 70)
        location_fit = st.slider("Location Fit Score", 0, 100, 90)

    run_analysis = st.form_submit_button("Run Analysis")

if run_analysis:
    if not company.strip():
        st.error("Company is required.")
        st.stop()

    if not position.strip():
        st.error("Position is required.")
        st.stop()

    if not job_description or len(job_description.strip()) < 80:
        st.error("Please paste a meaningful job description (at least ~80 characters).")
        st.stop()

    tech_score = weighted_technical_score(
        treasury_hedging, project_finance, debt_funding, seniority, tools_systems, location_fit
    )
    board_scores, board_avg = compute_board_scores(position, job_description, country)
    f_score = final_score(tech_score, board_avg)

    auto_excluded = exclusion_detected(position, job_description)

    st.session_state.analysis_result = {
        "company": company,
        "position": position,
        "location": location,
        "country": country,
        "source": source,
        "application_link": application_link,
        "job_description": job_description,
        "treasury_hedging": treasury_hedging,
        "project_finance": project_finance,
        "debt_funding": debt_funding,
        "seniority": seniority,
        "tools_systems": tools_systems,
        "location_fit": location_fit,
        "tech_score": round(tech_score, 2),
        "board_scores": board_scores,
        "board_avg": board_avg,
        "final_score": round(f_score, 2),
        "auto_excluded": auto_excluded,
    }

# Show analysis block only after clicking Run Analysis
result = st.session_state.analysis_result
if result:
    st.divider()
    st.subheader("Analysis Results")

    c1, c2, c3 = st.columns(3)
    c1.metric("Weighted Technical Score", f"{result['tech_score']} / 100")
    c2.metric("Board Overview Score", f"{result['board_avg']} / 100")
    c3.metric("Final Score", f"{result['final_score']} / 100")

    if result["auto_excluded"]:
        st.warning("Auto exclusion detected from role/title keywords. Review before saving.")

    st.markdown("### Board Details")
    for member in BOARD_MEMBERS:
        data = result["board_scores"].get(member, {})
        cc1, cc2 = st.columns([1, 3])
        with cc1:
            st.metric(member, f"{data.get('weighted_score', 0):.2f}")
        with cc2:
            st.caption(data.get("reason", ""))

    verified_active = st.checkbox("Role verified active", value=True)
    excluded_manual = st.checkbox("Out of scope / excluded (manual override)", value=False)

    if st.button("Save Job"):
        if exists_duplicate(result["company"], result["position"], result["country"]):
            st.warning("Duplicate detected: same Company + Position + Country already exists.")
            st.stop()

        excluded = excluded_manual or result["auto_excluded"]
        rec = recommendation(result["final_score"], verified_active=verified_active, excluded=excluded)
        prio = priority(result["final_score"], excluded=excluded)

        new_job = {
            "Company": result["company"].strip(),
            "Position": result["position"].strip(),
            "Location": result["location"].strip(),
            "Country": result["country"],
            "Source": result["source"].strip(),
            "Application Link": result["application_link"].strip(),
            "Job Description": result["job_description"].strip(),
            "Treasury/Hedging": result["treasury_hedging"],
            "Project Finance": result["project_finance"],
            "Debt/Funding": result["debt_funding"],
            "Seniority": result["seniority"],
            "Tools/Systems": result["tools_systems"],
            "Location Fit": result["location_fit"],
            "Weighted Technical Score": result["tech_score"],
            "Board Method": "Profile-aware board (95% description / 5% title)",
            "Board Overview Score": result["board_avg"],
            "Board Avg": result["board_avg"],
            "Final Score": result["final_score"],
            "Recommendation": rec,
            "Priority": prio,
            "Verified Active": verified_active,
            "Excluded": excluded,
            "Status": "Open" if verified_active and not excluded else "Excluded",
            "Board Scores": result["board_scores"],
            "Board Feedback": {},
        }

        save_job(new_job)
        st.session_state.jobs = load_jobs()
        st.success("Job saved successfully.")
        st.session_state.analysis_result = None

st.divider()
st.subheader("Dashboard Metrics")

jobs = st.session_state.jobs
total_jobs = len(jobs)
apply_now = sum(1 for j in jobs if j["Recommendation"] == "Apply Now")
consider_count = sum(1 for j in jobs if j["Recommendation"] == "Consider")
skip_count = sum(1 for j in jobs if j["Recommendation"] == "Skip")
avg_final_score = round(sum(j["Final Score"] for j in jobs) / total_jobs, 2) if total_jobs else 0.0
avg_board = round(sum(j.get("Board Avg", 0) for j in jobs) / total_jobs, 2) if total_jobs else 0.0

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Total Jobs", total_jobs)
m2.metric("Apply Now", apply_now)
m3.metric("Consider", consider_count)
m4.metric("Skip", skip_count)
m5.metric("Avg Final Score", avg_final_score)
m6.metric("Avg Board Overview", avg_board)

st.divider()
st.subheader("Jobs Table")

if total_jobs == 0:
    st.info("No jobs added yet.")
else:
    df = pd.DataFrame(jobs)

    display_cols = [
        "Company", "Position", "Country", "Source",
        "Weighted Technical Score", "Board Overview Score", "Final Score",
        "Recommendation", "Priority", "Status", "Excluded"
    ]
    display_df = df[display_cols].copy()

    c1, c2, c3 = st.columns(3)
    with c1:
        rec_filter = st.selectbox("Filter by Recommendation", ["All"] + sorted(display_df["Recommendation"].dropna().unique().tolist()))
    with c2:
        country_filter = st.selectbox("Filter by Country", ["All"] + sorted(display_df["Country"].dropna().unique().tolist()))
    with c3:
        status_filter = st.selectbox("Filter by Status", ["All"] + sorted(display_df["Status"].dropna().unique().tolist()))

    filtered = display_df.copy()
    if rec_filter != "All":
        filtered = filtered[filtered["Recommendation"] == rec_filter]
    if country_filter != "All":
        filtered = filtered[filtered["Country"] == country_filter]
    if status_filter != "All":
        filtered = filtered[filtered["Status"] == status_filter]

    st.dataframe(filtered, use_container_width=True)

    st.markdown("### Detailed Board Analysis")
    for i, job in enumerate(jobs, start=1):
        header = f"{i}. {job['Company']} - {job['Position']} | Board: {job.get('Board Avg', 0)} | Final: {job['Final Score']}"
        with st.expander(header):
            st.write("**Job Description**")
            st.write(job.get("Job Description", ""))
            st.write("**Board Scores**")
            st.json(job.get("Board Scores", {}))
