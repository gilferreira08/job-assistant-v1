import streamlit as st
import pandas as pd

from scoring import weighted_technical_score, final_score, recommendation, priority
from knowledge import TARGET_GEOS, BOARD_MEMBERS

st.set_page_config(page_title="Treasury Job Assistant", layout="wide")
st.title("Treasury / Project Finance Job Assistant (Lean MVP)")
st.caption("Board scoring logic: 95% based on Job Description, 5% based on Position Title.")

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
        source = st.text_input("Source (LinkedIn, eFinancialCareers, etc.)")
        application_link = st.text_input("Application Link")
        job_description = st.text_area(
            "Job Description (required)",
            height=220,
            help="Paste the full job description text here."
        )

    with col2:
        treasury_hedging = st.slider("Treasury / Hedging Score", 0, 100, 70)
        project_finance = st.slider("Project Finance Score", 0, 100, 70)
        debt_funding = st.slider("Debt / Funding Score", 0, 100, 70)
        seniority = st.slider("Seniority Score", 0, 100, 70)
        tools_systems = st.slider("Tools & Systems Score", 0, 100, 70)
        location_fit = st.slider("Location Fit Score", 0, 100, 90)

    st.markdown("### Board Analysis (95% Description / 5% Title)")

    board_scores = {}
    board_feedback = {}

    for member in BOARD_MEMBERS:
        st.markdown(f"**{member}**")
        c1, c2, c3 = st.columns([1, 1, 2])

        with c1:
            desc_score = st.slider(
                f"{member} - Description Score",
                0, 100, 75,
                key=f"desc_{member}"
            )

        with c2:
            title_score = st.slider(
                f"{member} - Title Score",
                0, 100, 70,
                key=f"title_{member}"
            )

        weighted_member_score = round((desc_score * 0.95) + (title_score * 0.05), 2)
        board_scores[member] = {
            "description_score": desc_score,
            "title_score": title_score,
            "weighted_score": weighted_member_score,
        }

        with c3:
            board_feedback[member] = st.text_area(
                f"{member} Feedback (optional)",
                "",
                key=f"feedback_{member}",
                height=80
            )

    verified_active = st.checkbox("Role verified active", value=True)
    excluded = st.checkbox("Out of scope / excluded", value=False)

    submitted = st.form_submit_button("Save Job")

if submitted:
    # Basic validation
    if not company.strip():
        st.error("Company is required.")
        st.stop()

    if not position.strip():
        st.error("Position is required.")
        st.stop()

    if not job_description or len(job_description.strip()) < 80:
        st.error("Please paste a meaningful job description (at least ~80 characters).")
        st.stop()

    # Duplicate check (company + position + country)
    duplicate = any(
        j["Company"].strip().lower() == company.strip().lower()
        and j["Position"].strip().lower() == position.strip().lower()
        and j["Country"] == country
        for j in st.session_state.jobs
    )
    if duplicate:
        st.warning("Duplicate detected: same Company + Position + Country already exists.")
        st.stop()

    tech_score = weighted_technical_score(
        treasury_hedging,
        project_finance,
        debt_funding,
        seniority,
        tools_systems,
        location_fit,
    )

    board_avg = round(
        sum(v["weighted_score"] for v in board_scores.values()) / len(board_scores),
        2
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
        "Job Description": job_description.strip(),
        "Treasury/Hedging": treasury_hedging,
        "Project Finance": project_finance,
        "Debt/Funding": debt_funding,
        "Seniority": seniority,
        "Tools/Systems": tools_systems,
        "Location Fit": location_fit,
        "Weighted Technical Score": round(tech_score, 2),
        "Board Method": "95% Description / 5% Title",
        "Board Avg": board_avg,
        "Final Score": round(f_score, 2),
        "Recommendation": rec,
        "Priority": prio,
        "Verified Active": verified_active,
        "Excluded": excluded,
        "Status": "Open" if verified_active and not excluded else "Excluded",
        "Board Scores": board_scores,
        "Board Feedback": board_feedback,
    }

    st.session_state.jobs.append(new_job)
    st.success("Job saved successfully.")

st.divider()
st.subheader("Dashboard Metrics")

jobs = st.session_state.jobs
total_jobs = len(jobs)
apply_now = sum(1 for j in jobs if j["Recommendation"] == "Apply Now")
consider_count = sum(1 for j in jobs if j["Recommendation"] == "Consider")
skip_count = sum(1 for j in jobs if j["Recommendation"] == "Skip")
avg_final_score = round(sum(j["Final Score"] for j in jobs) / total_jobs, 2) if total_jobs else 0.0

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Jobs", total_jobs)
m2.metric("Apply Now", apply_now)
m3.metric("Consider", consider_count)
m4.metric("Skip", skip_count)
m5.metric("Avg Final Score", avg_final_score)

st.divider()
st.subheader("Jobs Table")

if total_jobs == 0:
    st.info("No jobs added yet.")
else:
    df = pd.DataFrame(jobs)

    # Keep table readable by hiding very large nested fields
    display_cols = [
        "Company", "Position", "Location", "Country", "Source",
        "Weighted Technical Score", "Board Avg", "Final Score",
        "Recommendation", "Priority", "Status", "Verified Active", "Excluded"
    ]
    display_df = df[display_cols].copy()

    f1, f2, f3 = st.columns(3)
    with f1:
        rec_filter = st.selectbox(
            "Filter by Recommendation",
            ["All"] + sorted(display_df["Recommendation"].unique().tolist())
        )
    with f2:
        country_filter = st.selectbox(
            "Filter by Country",
            ["All"] + sorted(display_df["Country"].unique().tolist())
        )
    with f3:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All"] + sorted(display_df["Status"].unique().tolist())
        )

    filtered_df = display_df.copy()
    if rec_filter != "All":
        filtered_df = filtered_df[filtered_df["Recommendation"] == rec_filter]
    if country_filter != "All":
        filtered_df = filtered_df[filtered_df["Country"] == country_filter]
    if status_filter != "All":
        filtered_df = filtered_df[filtered_df["Status"] == status_filter]

    st.dataframe(filtered_df, use_container_width=True)

    st.markdown("### Detailed Board Analysis")
    for i, job in enumerate(jobs, start=1):
        header = f"{i}. {job['Company']} - {job['Position']} ({job['Country']}) | Final: {job['Final Score']}"
        with st.expander(header):
            st.write("**Job Description**")
            st.write(job.get("Job Description", ""))

            st.write("**Board Method**")
            st.write(job.get("Board Method", "95% Description / 5% Title"))

            st.write("**Board Average**")
            st.write(job.get("Board Avg"))

            st.write("**Board Scores**")
            st.json(job.get("Board Scores", {}))

            st.write("**Board Feedback**")
            st.json(job.get("Board Feedback", {}))
