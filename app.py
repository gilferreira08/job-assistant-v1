import json
from datetime import datetime

import pandas as pd
import streamlit as st

from interview_agent import generate_interview_assessment
from knowledge import BOARD_MEMBERS, TARGET_GEOS
from scoring import (
    auto_technical_suggestion,
    compute_board_scores,
    exclusion_detected,
    exclusion_reason,
    final_score,
    priority,
    recommendation,
    weighted_technical_score,
)
from storage import (
    delete_job_by_id,
    exists_duplicate,
    export_jobs_backup,
    find_duplicate_id,
    init_db,
    load_jobs,
    restore_jobs_backup,
    save_job,
)

st.set_page_config(page_title="Treasury Job Assistant", layout="wide")
st.title("Treasury / Project Finance Job Assistant (Lean MVP)")
st.caption("Paste job info (EN or FR), then click Run Analysis.")

init_db()

if "jobs" not in st.session_state:
    st.session_state.jobs = load_jobs()

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "gpt_interview_assessment" not in st.session_state:
    st.session_state.gpt_interview_assessment = ""


# -----------------------------------------------------------------------------
# Backup / Restore sidebar
# -----------------------------------------------------------------------------
st.sidebar.subheader("Backup / Restore")

backup_data = export_jobs_backup()
backup_json = json.dumps(backup_data, ensure_ascii=False, indent=2)
backup_filename = f"job_assistant_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json"

st.sidebar.download_button(
    label="Download backup JSON",
    data=backup_json,
    file_name=backup_filename,
    mime="application/json",
)

restore_file = st.sidebar.file_uploader("Restore backup JSON", type=["json"])
replace_existing = st.sidebar.checkbox("Replace existing jobs during restore", value=False)

if restore_file is not None:
    if st.sidebar.button("Restore backup"):
        restored_jobs = json.load(restore_file)
        restored_count = restore_jobs_backup(restored_jobs, replace_existing=replace_existing)
        st.session_state.jobs = load_jobs()
        st.sidebar.success(f"Restored {restored_count} jobs.")
        st.rerun()


# -----------------------------------------------------------------------------
# Add job / analysis form
# -----------------------------------------------------------------------------
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
    st.session_state.gpt_interview_assessment = ""

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
        treasury_hedging,
        project_finance,
        debt_funding,
        seniority,
        tools_systems,
        location_fit,
    )
    blended_tech_score = round(
        (auto_tech["weighted_technical_score"] * 0.70) + (manual_tech_score * 0.30),
        2,
    )

    board_scores, board_avg = compute_board_scores(position, job_description, country)
    if not isinstance(board_scores, dict):
        board_scores = {}
    if board_avg is None:
        board_avg = 0.0

    f_score = final_score(blended_tech_score, board_avg)
    auto_excluded = exclusion_detected(position, job_description)
    auto_excl_reason = exclusion_reason(position, job_description)
    preview_recommendation = recommendation(
        f_score,
        verified_active=True,
        excluded=auto_excluded,
    )
    preview_priority = priority(f_score, excluded=auto_excluded)

    st.session_state.analysis_result = {
        "company": company,
        "position": position,
        "location": location,
        "country": country,
        "source": source,
        "application_link": application_link,
        "job_description": job_description,
        "interview_notes": "",
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
        "recommendation_preview": preview_recommendation,
        "priority_preview": preview_priority,
        "auto_excluded": auto_excluded,
        "auto_exclusion_reason": auto_excl_reason,
    }


# -----------------------------------------------------------------------------
# Analysis results / save job
# -----------------------------------------------------------------------------
result = st.session_state.analysis_result

if result is not None:
    st.divider()
    st.subheader("Analysis Results")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Technical Score (Blended)", f"{result.get('blended_technical_score', 0)} / 100")
    c2.metric("Board Overview Score", f"{result.get('board_avg', 0)} / 100")
    c3.metric("Final Score", f"{result.get('final_score', 0)} / 100")
    c4.metric("Preview Recommendation", result.get("recommendation_preview", "N/A"))

    st.caption("Technical (Blended) = 70% Auto (JD-based) + 30% Manual sliders.")

    c5, c6 = st.columns(2)
    with c5:
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

    with c6:
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

    st.markdown("### Interview Notes / GPT Preparation")
    interview_notes = st.text_area(
        "Interview Notes / Feedback / Next Step",
        value=result.get("interview_notes", ""),
        height=160,
        help="Free-form notes for interview preparation, feedback, objections, and next actions.",
    )

    if st.button("Ask GPT to assess interview notes"):
        if not interview_notes.strip():
            st.warning("Please write or paste interview notes first.")
        else:
            api_key = None
            try:
                api_key = st.secrets.get("OPENAI_API_KEY")
            except Exception:
                api_key = None

            if not api_key:
                st.warning(
                    "Missing OPENAI_API_KEY. Add it in Streamlit secrets before using GPT assessment."
                )
            else:
                with st.spinner("GPT is assessing your interview notes..."):
                    st.session_state.gpt_interview_assessment = generate_interview_assessment(
                        company=result.get("company", ""),
                        position=result.get("position", ""),
                        job_description=result.get("job_description", ""),
                        final_score=result.get("final_score", 0),
                        board_avg=result.get("board_avg", 0),
                        recommendation=result.get("recommendation_preview", ""),
                        interview_notes=interview_notes,
                        api_key=api_key,
                    )

    if st.session_state.gpt_interview_assessment:
        st.markdown("### GPT Interview Assessment")
        st.write(st.session_state.gpt_interview_assessment)
        st.caption("If useful, copy the key points into the Interview Notes field before saving.")

    verified_active = st.checkbox("Role verified active", value=True)
    excluded_manual = st.checkbox("Out of scope / excluded (manual override)", value=False)

    is_dup = exists_duplicate(result["company"], result["position"], result["country"])
    duplicate_action = "Discard new"

    if is_dup:
        st.warning("Duplicate detected for same Company + Position + Country.")
        duplicate_action = st.selectbox(
            "Duplicate handling",
            ["Discard new", "Add anyway", "Replace existing"],
            index=0,
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
            excluded_reason = "manual override + " + (
                result.get("auto_exclusion_reason") or "automatic exclusion keyword match"
            )
        elif excluded_manual:
            excluded_reason = "manual override"
        elif result.get("auto_excluded", False):
            excluded_reason = result.get("auto_exclusion_reason") or "automatic exclusion keyword match"
        else:
            excluded_reason = ""

        rec = recommendation(
            result.get("final_score", 0),
            verified_active=verified_active,
            excluded=excluded,
        )
        prio = priority(result.get("final_score", 0), excluded=excluded)

        new_job = {
            "Company": result.get("company", "").strip(),
            "Position": result.get("position", "").strip(),
            "Location": result.get("location", "").strip(),
            "Country": result.get("country", ""),
            "Source": result.get("source", "").strip(),
            "Application Link": result.get("application_link", "").strip(),
            "Job Description": result.get("job_description", "").strip(),
            "Interview Notes": interview_notes,
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
        st.session_state.gpt_interview_assessment = ""
        st.rerun()


# -----------------------------------------------------------------------------
# Dashboard metrics
# -----------------------------------------------------------------------------
st.divider()
st.subheader("Dashboard Metrics")

jobs = st.session_state.jobs
total_jobs = len(jobs)
apply_now = sum(1 for j in jobs if j.get("Recommendation") == "Apply Now")
consider_count = sum(1 for j in jobs if j.get("Recommendation") == "Consider")
skip_count = sum(1 for j in jobs if j.get("Recommendation") == "Skip")
open_count = sum(1 for j in jobs if j.get("Status") == "Open")
interview_count = sum(1 for j in jobs if j.get("Status") == "Interview")
avg_final_score = round(sum(j.get("Final Score", 0) for j in jobs) / total_jobs, 2) if total_jobs else 0.0
avg_board = round(sum(j.get("Board Avg", 0) for j in jobs) / total_jobs, 2) if total_jobs else 0.0

m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
m1.metric("Total Jobs", total_jobs)
m2.metric("Open", open_count)
m3.metric("Interviews", interview_count)
m4.metric("Apply Now", apply_now)
m5.metric("Consider", consider_count)
m6.metric("Skip", skip_count)
m7.metric("Avg Final", avg_final_score)

st.caption(f"Average Board Overview: {avg_board}")


# -----------------------------------------------------------------------------
# Jobs table / detail expanders
# -----------------------------------------------------------------------------
st.divider()
st.subheader("Jobs Table")

if total_jobs == 0:
    st.info("No jobs added yet.")
else:
    df = pd.DataFrame(jobs)

    required_columns = {
        "Auto Technical Score": None,
        "Manual Technical Score": None,
        "Weighted Technical Score": None,
        "Board Overview Score": None,
        "Final Score": None,
        "Recommendation": "",
        "Priority": "",
        "Status": "",
        "Excluded": False,
        "Excluded Reason": "",
        "Interview Notes": "",
        "Country": "",
        "Source": "",
    }

    for col, default in required_columns.items():
        if col not in df.columns:
            df[col] = default

    display_cols = [
        "Company",
        "Position",
        "Country",
        "Source",
        "Auto Technical Score",
        "Manual Technical Score",
        "Weighted Technical Score",
        "Board Overview Score",
        "Final Score",
        "Recommendation",
        "Priority",
        "Status",
        "Excluded",
        "Excluded Reason",
        "Interview Notes",
    ]

    display_df = df[display_cols].copy()

    f1, f2, f3 = st.columns(3)
    with f1:
        rec_filter = st.selectbox(
            "Filter by Recommendation",
            ["All"] + sorted(display_df["Recommendation"].dropna().unique().tolist()),
        )
    with f2:
        country_filter = st.selectbox(
            "Filter by Country",
            ["All"] + sorted(display_df["Country"].dropna().unique().tolist()),
        )
    with f3:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All"] + sorted(display_df["Status"].dropna().unique().tolist()),
        )

    filtered = display_df.copy()
    if rec_filter != "All":
        filtered = filtered[filtered["Recommendation"] == rec_filter]
    if country_filter != "All":
        filtered = filtered[filtered["Country"] == country_filter]
    if status_filter != "All":
        filtered = filtered[filtered["Status"] == status_filter]

    st.dataframe(filtered, width="stretch")

    st.markdown("### Detailed Board Analysis")
    for i, job in enumerate(jobs, start=1):
        header = (
            f"{i}. {job.get('Company', '')} - {job.get('Position', '')} "
            f"| Board: {job.get('Board Avg', 0)} | Final: {job.get('Final Score', 0)} "
            f"| Status: {job.get('Status', '')}"
        )
        with st.expander(header):
            st.write("**Job Description**")
            st.write(job.get("Job Description", "") or "No job description saved.")

            st.write("**Interview Notes / Feedback / Next Step**")
            st.write(job.get("Interview Notes", "") or "No interview notes yet.")

            st.write("**Technical Breakdown**")
            st.write(f"- Auto Technical: {job.get('Auto Technical Score', 'N/A')}")
            st.write(f"- Manual Technical: {job.get('Manual Technical Score', 'N/A')}")
            st.write(f"- Blended Technical: {job.get('Weighted Technical Score', 'N/A')}")

            st.write("**Exclusion**")
            st.write(f"- Excluded: {job.get('Excluded', False)}")
            st.write(f"- Excluded Reason: {job.get('Excluded Reason', '') or 'None'}")

            st.write("**Board Scores**")
            st.json(job.get("Board Scores", {}))
