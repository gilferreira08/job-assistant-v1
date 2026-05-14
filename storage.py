import sqlite3
import json
from typing import List, Dict, Any

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
            board_method TEXT,
            board_avg REAL,
            final_score REAL,
            recommendation TEXT,
            priority TEXT,
            verified_active INTEGER,
            excluded INTEGER,
            status TEXT,
            board_scores_json TEXT,
            board_feedback_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def save_job(job: Dict[str, Any]):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO jobs (
            company, position, location, country, source, application_link, job_description,
            treasury_hedging, project_finance, debt_funding, seniority, tools_systems, location_fit,
            weighted_technical_score, board_method, board_avg, final_score, recommendation, priority,
            verified_active, excluded, status, board_scores_json, board_feedback_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.get("Company"),
            job.get("Position"),
            job.get("Location"),
            job.get("Country"),
            job.get("Source"),
            job.get("Application Link"),
            job.get("Job Description"),
            job.get("Treasury/Hedging"),
            job.get("Project Finance"),
            job.get("Debt/Funding"),
            job.get("Seniority"),
            job.get("Tools/Systems"),
            job.get("Location Fit"),
            job.get("Weighted Technical Score"),
            job.get("Board Method"),
            job.get("Board Avg"),
            job.get("Final Score"),
            job.get("Recommendation"),
            job.get("Priority"),
            1 if job.get("Verified Active") else 0,
            1 if job.get("Excluded") else 0,
            job.get("Status"),
            json.dumps(job.get("Board Scores", {}), ensure_ascii=False),
            json.dumps(job.get("Board Feedback", {}), ensure_ascii=False),
        ),
    )

    conn.commit()
    conn.close()


def load_jobs() -> List[Dict[str, Any]]:
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
                "Board Method": r["board_method"],
                "Board Avg": r["board_avg"],
                "Final Score": r["final_score"],
                "Recommendation": r["recommendation"],
                "Priority": r["priority"],
                "Verified Active": bool(r["verified_active"]),
                "Excluded": bool(r["excluded"]),
                "Status": r["status"],
                "Board Scores": json.loads(r["board_scores_json"] or "{}"),
                "Board Feedback": json.loads(r["board_feedback_json"] or "{}"),
            }
        )
    return jobs


def exists_duplicate(company: str, position: str, country: str) -> bool:
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
