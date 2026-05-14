import sqlite3
import json

DB_PATH = "jobs.db"


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


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
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO jobs (
            company, position, location, country, source, application_link, job_description,
            treasury_hedging, project_finance, debt_funding, seniority, tools_systems, location_fit,
            weighted_technical_score, auto_technical_score, manual_technical_score,
            board_method, board_avg, final_score, recommendation, priority,
            verified_active, excluded, excluded_reason, status, board_scores_json, board_feedback_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.get("Company", ""),
            job.get("Position", ""),
            job.get("Location", ""),
            job.get("Country", ""),
            job.get("Source", ""),
            job.get("Application Link", ""),
            job.get("Job Description", ""),
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


def load_jobs():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()

    jobs = []
    for r in rows:
        jobs.append(
            {
                "id": r["id"],
                "Company": r["company"],
                "Position": r["position"],
                "Location": r["location"],
                "Country": r["country"],
                "Source": r["source"],
                "Application Link": r["application_link"],
                "Job Description": r["job_description"],
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
                "Board Scores": json.loads(r["board_scores_json"] or "{}"),
                "Board Feedback": json.loads(r["board_feedback_json"] or "{}"),
            }
        )
    return jobs


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
