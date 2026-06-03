import json
import sqlite3

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
            company TEXT,
            position TEXT,
            location TEXT,
            country TEXT,
            source TEXT,
            application_link TEXT,
            job_description TEXT,
            final_score REAL,
            recommendation TEXT,
            status TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def save_job(job):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO jobs (
            company, position, location, country, source, application_link,
            job_description, final_score, recommendation, status, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.get("Company", ""),
            job.get("Position", ""),
            job.get("Location", ""),
            job.get("Country", ""),
            job.get("Source", ""),
            job.get("Application Link", ""),
            job.get("Job Description", ""),
            job.get("Final Score", 0),
            job.get("Recommendation", ""),
            job.get("Status", "Open"),
            job.get("Notes", ""),
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
    for row in rows:
        jobs.append(
            {
                "id": row["id"],
                "Company": row["company"] or "",
                "Position": row["position"] or "",
                "Location": row["location"] or "",
                "Country": row["country"] or "",
                "Source": row["source"] or "",
                "Application Link": row["application_link"] or "",
                "Job Description": row["job_description"] or "",
                "Final Score": row["final_score"] or 0,
                "Recommendation": row["recommendation"] or "",
                "Status": row["status"] or "Open",
                "Notes": row["notes"] or "",
            }
        )
    return jobs


def export_jobs_backup():
    return load_jobs()


def clear_jobs():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM jobs")
    conn.commit()
    conn.close()


def restore_jobs_backup(jobs, replace_existing=False):
    if replace_existing:
        clear_jobs()

    restored = 0
    for job in jobs:
        save_job(job)
        restored += 1

    return restored


def backup_to_json_text():
    return json.dumps(export_jobs_backup(), ensure_ascii=False, indent=2)
