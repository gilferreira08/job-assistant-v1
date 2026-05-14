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
    exclusion_reason,
    auto_technical_suggestion,
)
from storage import (
    init_db,
    load_jobs,
    save_job,
    exists_duplicate,
    find_duplicate_id,
    delete_job_by_id,
)

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
        treasury_hedging = st.slider("Treasury / Hedging Score (manual)", 0, 100, 70)
        project_finance = st.slider("Project Finance Score (manual)", 0, 100, 70)
        debt_funding = st.slider("Debt / Funding Score (manual)", 0, 100, 70)
        seniority = st.slider("Seniority Score (manual)", 0, 100, 70)
        tools_systems = st.slider("Tools & Systems Score (manual)", 0, 100, 70)
        location_fit = st.slider("Location Fit Score (manual)", 0, 100, 90)

    run_analysis = st.form_submit_button("Run Analysis")

if run_analysis:
    if not company.strip():
        st.error("Company is required.")
        st.session_state.analysis_result = None
        st.stop()

    if not position.strip():
        st.error("Position is required.")
        st.session_state.analysis_result = None
        st.stop()

    if not job_description or len(job_description.strip()) < 80:
        st.error("Please paste a meaningful job description (at least ~80 characters).")
        st.session_state.analysis_result = None
        st.stop()

    auto_tech = auto_technical_suggestion(position, job_description, country)
    manual_tech_score = weighted_technical_score(
        treasury_hedging, project_finance, debt_funding, seniority, tools_systems, location_fit
    )
    blended_tech_score = round((auto_tech["weighted_technical_score"] * 0.70) + (manual_tech_score * 0.30), 2)

    board_scores, board_avg = compute_board_scores(position, job_description, country)
    if not isinstance(board_scores, dict):
        board_scores = {}
    if board_avg is None:
        board_avg = 0.0

    f_score = final_score(blended_tech_score, board_avg)
    auto_excluded = exclusion_detected(position, job_description)
    auto_excl_reason = exclusion_reason(position, job_description)

    st.session_state.analysis_result = {
        "company": company,
        "position": position,
        "location": location,
        "country": country,
        "source": source,
        "application_link": application_link,
        "job_description": job_description,
        "manual_scores": {
            "treasury_hedging": treasury_hedging,
            "project_finance": project_finance,
            "debt_funding": debt_funding,
            "seniority": seniority,
            "tools_systems": tools_systems,
            "location_fit": location_fit,
            "weighted_technical_score": round(manual_tech_score, 2),
        },
        "auto_scores": auto_tech,
        "blended_technical_score": blended_tech_score,
        "board_scores": board_scores,
        "board_avg": round(float(board_avg), 2),
        "final_score": round(f_score, 2),
        "auto_excluded": auto_excluded,
        "auto_exclusion_reason": auto_excl_reason,
    }

result = st.session_state.analysis_result
if result is not None:
    st.divider()
    st.subheader("Analysis Results")
    st.caption(f"Debug: board members loaded = {len(result.get('board_scores', {}))}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Technical Score (Blended)", f"{result.get('blended_technical_score', 0)} / 100")
    c2.metric("Board Overview Score", f"{result.get('board_avg', 0)} / 100")
    c3.metric("Final Score", f"{result.get('final_score', 0)} / 100")
    st.caption("Technical (Blended) = 70% Auto (JD-based) + 30% Manual sliders.")

    c4, c5 = st.columns(2)
    with c4:
        st.markdown("**Auto Technical Suggestion (from JD)**")
        auto = result.get("auto_scores", {})
        st.write(
            f"- Treasury/Hedging: {auto.get('treasury_hedging', 0)}\n"
            f"- Project Finance: {auto.get('project_finance', 0)}\n"
            f"- Debt/Funding: {auto.get('debt_funding', 0)}\n"
            f"- Seniority: {auto.get('seniority', 0)}\n"
            f"- Tools/Systems: {auto.get('tools_systems', 0)}\n"
            f"- Location Fit: {auto.get('location_fit', 0)}\n"
            f"- Weighted Technical (Auto): {auto.get('weighted_technical_score', 0)}"
        )

    with c5:
        st.markdown("**Manual Technical Inputs**")
        man = result.get("manual_scores", {})
        st.write(
            f"- Treasury/Hedging: {man.get('treasury_hedging', 0)}\n"
            f"- Project Finance: {man.get('project_finance', 0)}\n"
            f"- Debt/Funding: {man.get('debt_funding', 0)}\n"
            f"- Seniority: {man.get('seniority', 0)}\n"
            f"- Tools/Systems: {man.get('tools_systems', 0)}\n"
            f"- Location Fit: {man.get('location_fit', 0)}\n"
            f"- Weighted Technical (Manual): {man.get('weighted_technical_score', 0)}"
        )

    if result.get("auto_excluded", False):
        reason_txt = result.get("auto_exclusion_reason", "automatic exclusion keyword match")
        st.warning(f"Auto exclusion detected. Reason: {reason_txt}")

    st.markdown("### Board Details")
    board_data = result.get("board_scores", {})

    if not board_data:
        st.warning("Board analysis not available yet. Please click Run Analysis.")
    else:
        for member in BOARD_MEMBERS:
            data = board_data.get(member, {})
            cc1, cc2 = st.columns([1, 3])

            with cc1:
                st.metric(member, f"{data.get('weighted_score', 0):.2f}")

            with cc2:
                st.write(data.get("short_note", "No note available."))
                st.caption(data.get("reason", "No detailed reason available."))

    verified_active = st.checkbox("Role verified active", value=True)
    excluded_manual = st.checkbox("Out of scope / excluded (manual override)", value=False)

    # Duplicate flow
    is_dup = exists_duplicate(result["company"], result["position"], result["country"])
    duplicate_action = "Discard new"

    if is_dup:
        st.warning("Duplicate detected for same Company + Position + Country.")
        duplicate_action = st.selectbox(
            "Duplicate handling",
            ["Discard new", "Add anyway", "Replace existing"],
            index=0
        )

    if st.button("Save Job"):
        existing_id = find_duplicate_id(result["company"], result["position"], result["country"])

        if existing_id and duplicate_action == "Discard new":
            st.info("New record discarded (duplicate policy).")
            st.stop()

        if existing_id and duplicate_action == "Replace existing":
            delete_job_by_id(existing_id)

        excluded = excluded_manual or result.get("auto_excluded", False)

        if excluded_manual and result.get("auto_excluded", False):
            excluded_reason = "manual override + " + (result.get("auto_exclusion_reason") or "automatic exclusion keyword match")
        elif excluded_manual:
            excluded_reason = "manual override"
        elif result.get("auto_excluded", False):
            excluded_reason = result.get("auto_exclusion_reason") or "automatic exclusion keyword match"
        else:
            excluded_reason = ""

        rec = recommendation(result.get("final_score", 0), verified_active=verified_active, excluded=excluded)
        prio = priority(result.get("final_score", 0), excluded=excluded)

        new_job = {
            "Company": result.get("company", "").strip(),
            "Position": result.get("position", "").strip(),
            "Location": result.get("location", "").strip(),
            "Country": result.get("country", ""),
            "Source": result.get("source", "").strip(),
            "Application Link": result.get("application_link", "").strip(),
            "Job Description": result.get("job_description", "").strip(),

            "Treasury/Hedging": result.get("manual_scores", {}).get("treasury_hedging", 0),
            "Project Finance": result.get("manual_scores", {}).get("project_finance", 0),
            "Debt/Funding": result.get("manual_scores", {}).get("debt_funding", 0),
            "Seniority": result.get("manual_scores", {}).get("seniority", 0),
            "Tools/Systems": result.get("manual_scores", {}).get("tools_systems", 0),
            "Location Fit": result.get("manual_scores", {}).get("location_fit", 0),

            "Auto Technical Score": result.get("auto_scores", {}).get("weighted_technical_score", 0),
            "Manual Technical Score": result.get("manual_scores", {}).get("weighted_technical_score", 0),
            "Weighted Technical Score": result.get("blended_technical_score", 0),

            "Board Method": "Profile-aware board (95% description / 5% title)",
            "Board Overview Score": result.get("board_avg", 0),
            "Board Avg": result.get("board_avg", 0),
            "Final Score": result.get("final_score", 0),

            "Recommendation": rec,
            "Priority": prio,
            "Verified Active": verified_active,
            "Excluded": excluded,
            "Excluded Reason": excluded_reason,
            "Status": "Open" if verified_active and not excluded else "Excluded",
            "Board Scores": result.get("board_scores", {}),
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
apply_now = sum(1 for j in jobs if j.get("Recommendation") == "Apply Now")
consider_count = sum(1 for j in jobs if j.get("Recommendation") == "Consider")
skip_count = sum(1 for j in jobs if j.get("Recommendation") == "Skip")
avg_final_score = round(sum(j.get("Final Score", 0) for j in jobs) / total_jobs, 2) if total_jobs else 0.0
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

    if "Auto Technical Score" not in df.columns:
        df["Auto Technical Score"] = None
    if "Manual Technical Score" not in df.columns:
        df["Manual Technical Score"] = None
    if "Excluded Reason" not in df.columns:
        df["Excluded Reason"] = ""

    display_cols = [
        "Company", "Position", "Country", "Source",
        "Auto Technical Score", "Manual Technical Score", "Weighted Technical Score",
        "Board Overview Score", "Final Score",
        "Recommendation", "Priority", "Status", "Excluded", "Excluded Reason"
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
        header = (
            f"{i}. {job.get('Company', '')} - {job.get('Position', '')} "
            f"| Board: {job.get('Board Avg', 0)} | Final: {job.get('Final Score', 0)} "
            f"| Excluded Reason: {job.get('Excluded Reason', '') or 'None'}"
        )
        with st.expander(header):
            st.write("**Job Description**")
            st.write(job.get("Job Description", ""))

            st.write("**Technical Breakdown**")
            st.write(f"- Auto Technical: {job.get('Auto Technical Score', 'N/A')}")
            st.write(f"- Manual Technical: {job.get('Manual Technical Score', 'N/A')}")
            st.write(f"- Blended Technical: {job.get('Weighted Technical Score', 'N/A')}")

            st.write("**Exclusion**")
            st.write(f"- Excluded: {job.get('Excluded', False)}")
            st.write(f"- Excluded Reason: {job.get('Excluded Reason', '') or 'None'}")

            st.write("**Board Scores**")
            st.json(job.get("Board Scores", {}))
