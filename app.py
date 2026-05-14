import streamlit as st
import pandas as pd

from scoring import weighted_technical_score, final_score, recommendation, priority
from knowledge import TARGET_GEOS

st.set_page_config(page_title="Treasury Job Assistant", layout="wide")
st.title("Treasury / Project Finance Job Assistant (Lean MVP)")

if "jobs" not in st.session_state:
    st.session_state.jobs = []

st.subheader("Add Job")

with st.form("job_form"):
    col1, col2 = st.columns(2)

    with col1:
        company = st.text_input("Company")
        position = st.text_input("Position")
        location = st.text_input("Location")
        country = st.selectbox("Country", TARGET_GEOS + ["Other"])
        source = st.text_input("Source")
        application_link = st.text_input("Application Link")

    with col2:
        treasury_hedging = st.slider("Treasury / Hedging Score", 0, 100, 70)
        project_finance = st.slider("Project Finance Score", 0, 100, 70)
        debt_funding = st.slider("Debt / Funding Score", 0, 100, 70)
        seniority = st.slider("Seniority Score", 0, 100, 70)
        tools_systems = st.slider("Tools & Systems Score", 0, 100, 70)
        location_fit = st.slider("Location Fit Score", 0, 100, 90)
        board_avg = st.slider("Board Average Score", 0, 100, 75)

    verified_active = st.checkbox("Role verified active", value=True)
    excluded = st.checkbox("Out of scope / excluded", value=False)

    submitted = st.form_submit_button("Save Job")

if submitted:
    tech_score = weighted_technical_score(
        treasury_hedging,
        project_finance,
        debt_funding,
        seniority,
        tools_systems,
        location_fit,
    )
    f_score = final_score(tech_score, board_avg)
    rec = recommendation(f_score, verified_active=verified_active, excluded=excluded)
    prio = priority(f_score, excluded=excluded)

    new_job = {
        "Company": company.strip(),
        "Position": position.strip(),
        "Location": location.strip(),
        "Country": country,
        "Source": source.strip(),
        "Application Link": application_link.strip(),
        "Treasury/Hedging": treasury_hedging,
        "Project Finance": project_finance,
        "Debt/Funding": debt_funding,
        "Seniority": seniority,
        "Tools/Systems": tools_systems,
        "Location Fit": location_fit,
        "Board Avg": board_avg,
        "Weighted Technical Score": round(tech_score, 2),
        "Final Score": round(f_score, 2),
        "Recommendation": rec,
        "Priority": prio,
        "Verified Active": verified_active,
        "Excluded": excluded,
    }

    st.session_state.jobs.append(new_job)
    st.success("Job saved successfully.")

st.divider()
st.subheader("Dashboard Metrics")

jobs = st.session_state.jobs
total_jobs = len(jobs)
apply_now = sum(1 for j in jobs if j["Recommendation"] == "Apply Now")
consider = sum(1 for j in jobs if j["Recommendation"] == "Consider")
skip = sum(1 for j in jobs if j["Recommendation"] == "Skip")
avg_final_score = round(sum(j["Final Score"] for j in jobs) / total_jobs, 2) if total_jobs else 0.0

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Jobs", total_jobs)
m2.metric("Apply Now", apply_now)
m3.metric("Consider", consider)
m4.metric("Skip", skip)
m5.metric("Avg Final Score", avg_final_score)

st.divider()
st.subheader("Jobs Table")

if total_jobs == 0:
    st.info("No jobs added yet.")
else:
    df = pd.DataFrame(jobs)
    st.dataframe(df, use_container_width=True)
