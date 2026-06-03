import json
import sqlite3

DB_PATH = "jobs.db"


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def safe_json_loads(value, fallback):
    if not value:
        return fallback

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def normalize_interviews(interviews):
    if not isinstance(interviews, list):
        return []

    normalized = []
    for index, item in enumerate(interviews, start=1):
        if not isinstance(item, dict):
            continue

        number = item.get("number") or index
        try:
            number = int(number)
        except (TypeError, ValueError):
            number = index

        normalized.append(
            {
                "number": number,
                "date": str(item.get("date", "") or ""),
                "interviewer": str(item.get("interviewer", "") or ""),
                "notes": str(item.get("notes", "") or ""),
            }
        )

    return sorted(normalized, key=lambda x: x.get("number", 0))


def compile_interview_notes(interviews):
    compiled = []

    for interview in normalize_interviews(interviews):
        number = interview.get("number", "")
        date_value = interview.get("date", "")
        interviewer = interview.get("interviewer", "")
        notes = interview.get("notes", "")

        title_parts = [f"Interview #{number}"]

        if date_value:
            title_parts.append(date_value)

        if interviewer:
            title_parts.append(interviewer)

        compiled.append(" — ".join(title_parts))

        if notes:
            compiled.append(notes)

        compiled.append("")

    return "\n".join(compiled).strip()


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            position TEXT NOT NULL,
            location TEXT,
            country TEXT,
            source TEXT,
            application_link TEXT,
            job_description TEXT,
            interviews_json TEXT,
            interview_notes TEXT,
            interview_count INTEGER DEFAULT 0,
            interview_history TEXT,
            next_step TEXT,
            follow_up_date TEXT,
            follow_up_message TEXT,
            treasury_hedging REAL,
            project_finance REAL,
            debt_funding REAL,
            seniority REAL,
            tools_systems REAL,
            location_fit REAL,
            weighted_technical_score REAL,
            auto_technical_score REAL,
            manual_technical_score REAL,
            board_method TEXT,
            board_avg REAL,
            final_score REAL,
            recommendation TEXT,
            priority TEXT,
            verified_active INTEGER,
            excluded INTEGER,
            excluded_reason TEXT,
            status TEXT,
            board_scores_json TEXT,
            board_feedback_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    def add_column_if_missing(column_name, column_type):
        cur.execute("PRAGMA table_info(jobs)")
        existing = [row[1] for row in cur.fetchall()]

        if column_name not in existing:
            cur.execute(f"ALTER TABLE jobs ADD COLUMN {column_name} {column_type}")

    add_column_if_missing("location", "TEXT")
    add_column_if_missing("source", "TEXT")
    add_column_if_missing("application_link", "TEXT")
    add_column_if_missing("job_description", "TEXT")

    add_column_if_missing("interviews_json", "TEXT")
    add_column_if_missing("interview_notes", "TEXT")
    add_column_if_missing("interview_count", "INTEGER DEFAULT 0")
    add_column_if_missing("interview_history", "TEXT")
    add_column_if_missing("next_step", "TEXT")
    add_column_if_missing("follow_up_date", "TEXT")
    add_column_if_missing("follow_up_message", "TEXT")

    add_column_if_missing("treasury_hedging", "REAL")
    add_column_if_missing("project_finance", "REAL")
    add_column_if_missing("debt_funding", "REAL")
    add_column_if_missing("seniority", "REAL")
    add_column_if_missing("tools_systems", "REAL")
    add_column_if_missing("location_fit", "REAL")
    add_column_if_missing("weighted_technical_score", "REAL")
    add_column_if_missing("auto_technical_score", "REAL")
    add_column_if_missing("manual_technical_score", "REAL")

    add_column_if_missing("board_method", "TEXT")
    add_column_if_missing("board_avg", "REAL")
    add_column_if_missing("final_score", "REAL")
    add_column_if_missing("recommendation", "TEXT")
    add_column_if_missing("priority", "TEXT")

    add_column_if_missing("verified_active", "INTEGER")
    add_column_if_missing("excluded", "INTEGER")
    add_column_if_missing("excluded_reason", "TEXT")
    add_column_if_missing("status", "TEXT")

    add_column_if_missing("board_scores_json", "TEXT")
    add_column_if_missing("board_feedback_json", "TEXT")
    add_column_if_missing("created_at", "TEXT")

    conn.commit()
    conn.close()


def save_job(job):
    interviews = normalize_interviews(job.get("Interviews", []))
    compiled_notes = compile_interview_notes(interviews)

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO jobs (
            company, position, location, country, source, application_link,
            job_description, interviews_json, interview_notes, interview_count,
            interview_history, next_step, follow_up_date, follow_up_message,
            treasury_hedging, project_finance, debt_funding, seniority,
            tools_systems, location_fit,
            weighted_technical_score, auto_technical_score, manual_technical_score,
            board_method, board_avg, final_score, recommendation, priority,
            verified_active, excluded, excluded_reason, status,
            board_scores_json, board_feedback_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.get("Company", ""),
            job.get("Position", ""),
            job.get("Location", ""),
            job.get("Country", ""),
            job.get("Source", ""),
            job.get("Application Link", ""),
            job.get("Job Description", ""),

            json.dumps(interviews, ensure_ascii=False),
            job.get("All Notes and Feedbacks") or job.get("Interview Notes") or compiled_notes,
            len(interviews),
            job.get("Interview History") or compiled_notes,
            job.get("Next Step", ""),
            job.get("Follow-up Date", ""),
            job.get("Follow-up Message", ""),

            job.get("Treasury/Hedging", 0),
            job.get("Project Finance", 0),
            job.get("Debt/Funding", 0),
            job.get("Seniority", 0),
            job.get("Tools/Systems", 0),
            job.get("Location Fit", 0),
            job.get("Weighted Technical Score", 0),
            job.get("Auto Technical Score", 0),
            job.get("Manual Technical Score", 0),

            job.get("Board Method", ""),
            job.get("Board Avg", 0),
            job.get("Final Score", 0),
            job.get("Recommendation", ""),
            job.get("Priority", ""),

            1 if job.get("Verified Active", False) else 0,
            1 if job.get("Excluded", False) else 0,
            job.get("Excluded Reason", ""),
            job.get("Status", ""),

            json.dumps(job.get("Board Scores", {}), ensure_ascii=False),
            json.dumps(job.get("Board Feedback", {}), ensure_ascii=False),
        ),
    )

    conn.commit()
    conn.close()


def row_to_job(r):
    interviews = normalize_interviews(safe_json_loads(r["interviews_json"], []))
    compiled_notes = compile_interview_notes(interviews)
    stored_notes = r["interview_notes"] if r["interview_notes"] else ""

    return {
        "id": r["id"],
        "Company": r["company"],
        "Position": r["position"],
        "Location": r["location"],
        "Country": r["country"],
        "Source": r["source"],
        "Application Link": r["application_link"],
        "Job Description": r["job_description"],

        "Interviews": interviews,
        "Interviews JSON": json.dumps(interviews, ensure_ascii=False),
        "Interview Count": len(interviews),
        "Interview History": r["interview_history"] if r["interview_history"] else compiled_notes,
        "Interview Notes": stored_notes or compiled_notes,
        "All Notes and Feedbacks": compiled_notes or stored_notes,
        "Next Step": r["next_step"] if r["next_step"] else "",
        "Follow-up Date": r["follow_up_date"] if r["follow_up_date"] else "",
        "Follow-up Message": r["follow_up_message"] if r["follow_up_message"] else "",

        "Treasury/Hedging": r["treasury_hedging"],
        "Project Finance": r["project_finance"],
        "Debt/Funding": r["debt_funding"],
        "Seniority": r["seniority"],
        "Tools/Systems": r["tools_systems"],
        "Location Fit": r["location_fit"],
        "Weighted Technical Score": r["weighted_technical_score"],
        "Auto Technical Score": r["auto_technical_score"],
        "Manual Technical Score": r["manual_technical_score"],

        "Board Method": r["board_method"],
        "Board Overview Score": r["board_avg"],
        "Board Avg": r["board_avg"],
        "Final Score": r["final_score"],
        "Recommendation": r["recommendation"],
        "Priority": r["priority"],

        "Verified Active": bool(r["verified_active"]) if r["verified_active"] is not None else False,
        "Excluded": bool(r["excluded"]) if r["excluded"] is not None else False,
        "Excluded Reason": r["excluded_reason"] if r["excluded_reason"] else "",
        "Status": r["status"],

        "Board Scores": safe_json_loads(r["board_scores_json"], {}),
        "Board Feedback": safe_json_loads(r["board_feedback_json"], {}),
    }


def load_jobs():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM jobs ORDER BY id DESC")
    rows = cur.fetchall()

    conn.close()

    return [row_to_job(r) for r in rows]


def get_job_by_id(job_id):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cur.fetchone()

    conn.close()

    return row_to_job(row) if row else None


def update_hiring_process(
    job_id,
    status,
    next_step,
    follow_up_date,
    follow_up_message,
    interviews,
):
    interviews = normalize_interviews(interviews)
    compiled_notes = compile_interview_notes(interviews)

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE jobs
        SET status = ?,
            next_step = ?,
            follow_up_date = ?,
            follow_up_message = ?,
            interviews_json = ?,
            interview_count = ?,
            interview_history = ?,
            interview_notes = ?
        WHERE id = ?
        """,
        (
            status,
            next_step,
            follow_up_date,
            follow_up_message,
            json.dumps(interviews, ensure_ascii=False),
            len(interviews),
            compiled_notes,
            compiled_notes,
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def update_job_follow_up(
    job_id,
    status,
    interview_count=None,
    interview_history=None,
    interview_notes=None,
    next_step="",
    follow_up_date="",
    follow_up_message="",
):
    """Backward-compatible helper for older app.py versions."""
    interviews = []

    if interview_history or interview_notes:
        interviews = [
            {
                "number": 1,
                "date": "",
                "interviewer": "Historical notes",
                "notes": interview_notes or interview_history or "",
            }
        ]

    update_hiring_process(
        job_id=job_id,
        status=status,
        next_step=next_step,
        follow_up_date=follow_up_date,
        follow_up_message=follow_up_message,
        interviews=interviews,
    )


def exists_duplicate(company, position, country):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT 1 FROM jobs
        WHERE lower(company) = lower(?)
          AND lower(position) = lower(?)
          AND lower(country) = lower(?)
        LIMIT 1
        """,
        (company.strip(), position.strip(), country.strip()),
    )

    row = cur.fetchone()

    conn.close()

    return row is not None


def find_duplicate_id(company, position, country):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id FROM jobs
        WHERE lower(company) = lower(?)
          AND lower(position) = lower(?)
          AND lower(country) = lower(?)
        ORDER BY id DESC
        LIMIT 1
        """,
        (company.strip(), position.strip(), country.strip()),
    )

    row = cur.fetchone()

    conn.close()

    return row[0] if row else None


def delete_job_by_id(job_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM jobs WHERE id = ?", (job_id,))

    conn.commit()
    conn.close()


def export_jobs_backup():
    """Return all saved jobs as a JSON-serializable list."""
    return load_jobs()


def clear_jobs():
    """Delete all jobs from the local SQLite database."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM jobs")

    conn.commit()
    conn.close()


def restore_jobs_backup(jobs, replace_existing=False):
    """Restore jobs from a JSON backup file.

    If replace_existing=True, all current jobs are deleted first.
    """
    if replace_existing:
        clear_jobs()

    restored = 0

    for job in jobs:
        save_job(job)
        restored += 1

    return restored
