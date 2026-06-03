import json
from datetime import date, datetime

import pandas as pd
import streamlit as st

from knowledge import BOARD_MEMBERS, TARGET_GEOS
from scoring import (
    auto_technical_suggestion,
    compute_board_scores,
    exclusion_detected,
    exclusion_reason,
    final_score,
    priority,
    recommendation,
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
    update_job_follow_up,
)

APP_STATUSES = [
    "Open",
    "In Preparation",
    "Applied",
    "Interview",
    "Final Round",
    "Offer",
    "Rejected",
    "On Hold",
    "Closed",
    "Link Invalid",
    "Out of Scope",
    "Duplicate",
    "Excluded",
]

st.set_page_config(page_title="Treasury Job Assistant", layout="wide")
st.title("Treasury / Project Finance Job Assistant (Lean MVP)")
st.caption("Paste job info (EN or FR), then click Run Analysis.")

init_db()

if "jobs" not in st.session_state:
    st.session_state.jobs = load_jobs()

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None


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
        job_description = st.text_area("Job Description (required, EN or FR)", height=260)

    with col2:
        st.markdown("### Automatic Analysis")
        st.info(
            "Manual technical sliders were removed. The technical score is now generated from the job description."
        )
        st.write("The app will automatically estimate:")
        st.write("- Treasury / Hedging fit")
        st.write("- Project Finance exposure")
        st.write("- Debt / Funding / Refinancing fit")
        st.write("- Seniority")
        st.write("- Tools & Systems")
        st.write("- Location fit")

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
    technical_score = round(float(auto_tech.get("weighted_technical_score", 0)), 2)

    board_scores, board_avg = compute_board_scores(position, job_description, country)
    if not isinstance(board_scores, dict):
        board_scores = {}
    if board_avg is None:
        board_avg = 0.0

    f_score = final_score(technical_score, board_avg)
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
        "auto_scores": auto_tech,
        "technical_score": technical_score,
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
    c1.metric("Technical Score", f"{result.get('technical_score', 0)} / 100")
    c2.metric("Board Overview Score", f"{result.get('board_avg', 0)} / 100")
    c3.metric("Final Score", f"{result.get('final_score', 0)} / 100")
    c4.metric("Preview Recommendation", result.get("recommendation_preview", "N/A"))

    st.caption("Technical Score = automatic JD-based score. Manual technical inputs were removed.")

    st.markdown("### Automatic Technical Breakdown")
    auto = result.get("auto_scores", {})
    a1, a2, a3 = st.columns(3)
    a1.metric("Treasury / Hedging", auto.get("treasury_hedging", 0))
    a2.metric("Project Finance", auto.get("project_finance", 0))
    a3.metric("Debt / Funding", auto.get("debt_funding", 0))
    a4, a5, a6 = st.columns(3)
    a4.metric("Seniority", auto.get("seniority", 0))
    a5.metric("Tools / Systems", auto.get("tools_systems", 0))
    a6.metric("Location Fit", auto.get("location_fit", 0))

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
        status = "Open" if verified_active and not excluded else "Excluded"

        new_job = {
            "Company": result.get("company", "").strip(),
            "Position": result.get("position", "").strip(),
            "Location": result.get("location", "").strip(),
            "Country": result.get("country", ""),
            "Source": result.get("source", "").strip(),
            "Application Link": result.get("application_link", "").strip(),
            "Job Description": result.get("job_description", "").strip(),
            "Interview Notes": "",
            "Interview Count": 0,
            "Interview History": "",
            "Next Step": "",
            "Follow-up Date": "",
            "Follow-up Message": "",
            "Treasury/Hedging": result.get("auto_scores", {}).get("treasury_hedging", 0),
            "Project Finance": result.get("auto_scores", {}).get("project_finance", 0),
            "Debt/Funding": result.get("auto_scores", {}).get("debt_funding", 0),
            "Seniority": result.get("auto_scores", {}).get("seniority", 0),
            "Tools/Systems": result.get("auto_scores", {}).get("tools_systems", 0),
            "Location Fit": result.get("auto_scores", {}).get("location_fit", 0),
            "Auto Technical Score": result.get("technical_score", 0),
            "Manual Technical Score": None,
            "Weighted Technical Score": result.get("technical_score", 0),
            "Board Method": "Profile-aware board (95% description / 5% title)",
            "Board Overview Score": result.get("board_avg", 0),
            "Board Avg": result.get("board_avg", 0),
            "Final Score": result.get("final_score", 0),
            "Recommendation": rec,
            "Priority": prio,
            "Verified Active": verified_active,
            "Excluded": excluded,
            "Excluded Reason": excluded_reason,
            "Status": status,
            "Board Scores": result.get("board_scores", {}),
            "Board Feedback": {},
        }

        save_job(new_job)
        st.session_state.jobs = load_jobs()
        st.success("Job saved successfully.")
        st.session_state.analysis_result = None
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
applied_count = sum(1 for j in jobs if j.get("Status") == "Applied")
interview_count = sum(1 for j in jobs if j.get("Status") in ["Interview", "Final Round"])
follow_up_due = sum(1 for j in jobs if j.get("Follow-up Date") and j.get("Status") not in ["Rejected", "Closed", "Excluded"])
avg_final_score = round(sum(j.get("Final Score", 0) for j in jobs) / total_jobs, 2) if total_jobs else 0.0
avg_board = round(sum(j.get("Board Avg", 0) for j in jobs) / total_jobs, 2) if total_jobs else 0.0

m1, m2, m3, m4, m5, m6, m7, m8 = st.columns(8)
m1.metric("Total Jobs", total_jobs)
m2.metric("Open", open_count)
m3.metric("Applied", applied_count)
m4.metric("Interviews", interview_count)
m5.metric("Follow-ups", follow_up_due)
m6.metric("Apply Now", apply_now)
m7.metric("Consider", consider_count)
m8.metric("Avg Final", avg_final_score)

st.caption(f"Average Board Overview: {avg_board} | Skip: {skip_count}")


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
        "Weighted Technical Score": None,
        "Board Overview Score": None,
        "Final Score": None,
        "Recommendation": "",
        "Priority": "",
        "Status": "",
        "Excluded": False,
        "Excluded Reason": "",
        "Interview Count": 0,
        "Interview History": "",
        "Interview Notes": "",
        "Next Step": "",
        "Follow-up Date": "",
        "Follow-up Message": "",
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
        "Status",
        "Interview Count",
        "Next Step",
        "Follow-up Date",
        "Auto Technical Score",
        "Board Overview Score",
        "Final Score",
        "Recommendation",
        "Priority",
        "Excluded Reason",
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

            st.write("**Technical Breakdown**")
            st.write(f"- Auto Technical: {job.get('Auto Technical Score', 'N/A')}")
            st.write(f"- Technical Score: {job.get('Weighted Technical Score', 'N/A')}")

            st.write("**Exclusion**")
            st.write(f"- Excluded: {job.get('Excluded', False)}")
            st.write(f"- Excluded Reason: {job.get('Excluded Reason', '') or 'None'}")

            st.write("**Board Scores**")
            st.json(job.get("Board Scores", {}))

            st.markdown("#### Hiring Process Follow-up")

            current_status = job.get("Status", "Open") or "Open"
            status_index = APP_STATUSES.index(current_status) if current_status in APP_STATUSES else 0

            with st.form(f"follow_up_form_{job.get('id')}"):
                fu1, fu2 = st.columns(2)

                with fu1:
                    updated_status = st.selectbox(
                        "Application Status",
                        APP_STATUSES,
                        index=status_index,
                        key=f"status_{job.get('id')}",
                    )
                    updated_interview_count = st.number_input(
                        "Number of interviews already done",
                        min_value=0,
                        max_value=20,
                        value=int(job.get("Interview Count", 0) or 0),
                        step=1,
                        key=f"interview_count_{job.get('id')}",
                    )
                    updated_follow_up_date = st.date_input(
                        "Follow-up date",
                        value=date.fromisoformat(job.get("Follow-up Date")) if job.get("Follow-up Date") else date.today(),
                        key=f"follow_up_date_{job.get('id')}",
                    )
                    no_follow_up_date = st.checkbox(
                        "No follow-up date yet",
                        value=False if job.get("Follow-up Date") else True,
                        key=f"no_follow_up_{job.get('id')}",
                    )

                with fu2:
                    updated_next_step = st.text_input(
                        "Next step",
                        value=job.get("Next Step", ""),
                        placeholder="Example: Send thank-you note / Prepare Head of Treasury interview",
                        key=f"next_step_{job.get('id')}",
                    )
                    updated_follow_up_message = st.text_area(
                        "Follow-up message draft",
                        value=job.get("Follow-up Message", ""),
                        height=120,
                        key=f"follow_up_message_{job.get('id')}",
                    )

                updated_interview_history = st.text_area(
                    "Interview history: dates and people met",
                    value=job.get("Interview History", ""),
                    height=140,
                    placeholder="Example: 2026-06-03 — HR — discussed mobility, salary, timeline.\n2026-06-10 — Hiring Manager — discussed liquidity forecasting and hedging.",
                    key=f"interview_history_{job.get('id')}",
                )

                updated_interview_notes = st.text_area(
                    "Interview notes / feedback / next-step thinking",
                    value=job.get("Interview Notes", ""),
                    height=160,
                    key=f"interview_notes_{job.get('id')}",
                )

                save_follow_up = st.form_submit_button("Save Follow-up")

            if save_follow_up:
                follow_up_value = "" if no_follow_up_date else updated_follow_up_date.isoformat()
                update_job_follow_up(
                    job_id=job.get("id"),
                    status=updated_status,
                    interview_count=updated_interview_count,
                    interview_history=updated_interview_history,
                    interview_notes=updated_interview_notes,
                    next_step=updated_next_step,
                    follow_up_date=follow_up_value,
                    follow_up_message=updated_follow_up_message,
                )
                st.session_state.jobs = load_jobs()
                st.success("Hiring process follow-up updated.")
                st.rerun()
