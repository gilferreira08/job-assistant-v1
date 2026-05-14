import streamlit as st
import pandas as pd

from scoring import weighted_technical_score, final_score, recommendation, priority
from knowledge import TARGET_GEOS, BOARD_MEMBERS
from storage import init_db, load_jobs, save_job, exists_duplicate

st.set_page_config(page_title="Treasury Job Assistant", layout="wide")
st.title("Treasury / Project Finance Job Assistant (Lean MVP)")
st.caption("Board scoring logic: 95% based on Job Description, 5% based on Position Title.")

# --- DB init + load persisted jobs ---
init_db()
if "jobs" not in st.session_state:
    st.session_state.jobs = load_jobs()

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

    # DB duplicate check (company + position + country)
    duplicate = exists_duplicate(company, position, country)
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

    st.info(f"Board Overview Score (overall): **{board_avg} / 100**")

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
        "Board Overview Score": board_avg,
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

    # Save in SQLite and refresh session from DB
    save_job(new_job)
    st.session_state.jobs = load_jobs()
    st.success("Job saved successfully and persisted in database.")

st.divider()
st.subheader("Dashboard Metrics")

jobs = st.session_state.jobs
total_jobs = len(jobs)
apply_now = sum(1 for j in jobs if j["Recommendation"] == "Apply Now")
consider_count = sum(1 for j in jobs if j["Recommendation"] == "Consider")
skip_count = sum(1 for j in jobs if j["Recommendation"] == "Skip")
avg_final_score = round(sum(j["Final Score"] for j in jobs) / total_jobs, 2) if total_jobs else 0.0
avg_board_overview = round(
    sum(j.get("Board Overview Score", j.get("Board Avg", 0)) for j in jobs) / total_jobs, 2
) if total_jobs else 0.0

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Total Jobs", total_jobs)
m2.metric("Apply Now", apply_now)
m3.metric("Consider", consider_count)
m4.metric("Skip", skip_count)
m5.metric("Avg Final Score", avg_final_score)
m6.metric("Avg Board Overview", avg_board_overview)

st.divider()
st.subheader("Jobs Table")

if total_jobs == 0:
    st.info("No jobs added yet.")
else:
    df = pd.DataFrame(jobs)

    # Ensure Board Overview column exists for older rows
    if "Board Overview Score" not in df.columns:
        df["Board Overview Score"] = df.get("Board Avg", 0)

    display_cols = [
        "Company", "Position", "Location", "Country", "Source",
        "Weighted Technical Score", "Board Overview Score", "Board Avg", "Final Score",
        "Recommendation", "Priority", "Status", "Verified Active", "Excluded"
    ]
    display_df = df[display_cols].copy()

    f1, f2, f3 = st.columns(3)
    with f1:
        rec_filter = st.selectbox(
            "Filter by Recommendation",
            ["All"] + sorted(display_df["Recommendation"].dropna().unique().tolist())
        )
    with f2:
        country_filter = st.selectbox(
            "Filter by Country",
            ["All"] + sorted(display_df["Country"].dropna().unique().tolist())
        )
    with f3:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All"] + sorted(display_df["Status"].dropna().unique().tolist())
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
        board_overall = job.get("Board Overview Score", job.get("Board Avg"))
        header = (
            f"{i}. {job.get('Company', '')} - {job.get('Position', '')} "
            f"({job.get('Country', '')}) | Board: {board_overall} | Final: {job.get('Final Score', '')}"
        )
        with st.expander(header):
            st.write("**Job Description**")
            st.write(job.get("Job Description", ""))

            st.write("**Board Method**")
            st.write(job.get("Board Method", "95% Description / 5% Title"))

            st.write("**Board Overview Score (overall)**")
            st.write(board_overall)

            st.write("**Board Scores**")
            st.json(job.get("Board Scores", {}))

            st.write("**Board Feedback**")
            st.json(job.get("Board Feedback", {}))
