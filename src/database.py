
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "recruitai.db"


def get_connection():
    """Create the data directory and return a SQLite connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    """Create database tables if they do not already exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                required_skills TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS screenings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                candidate_name TEXT NOT NULL,
                filename TEXT NOT NULL,
                resume_text TEXT NOT NULL,
                matched_skills TEXT NOT NULL,
                not_found_skills TEXT NOT NULL,
                match_percentage REAL NOT NULL,
                ai_summary TEXT DEFAULT '',
                status TEXT DEFAULT 'Pending human review',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)


def create_job(title, description, required_skills):
    """Save a job and its required skills."""
    skills_text = "\n".join(
        skill.strip() for skill in required_skills if skill.strip()
    )

    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO jobs (title, description, required_skills)
               VALUES (?, ?, ?)""",
            (title.strip(), description.strip(), skills_text),
        )
        return cursor.lastrowid


def get_jobs():
    """Return all saved jobs."""
    with get_connection() as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC, id DESC"
            ).fetchall()
        ]


def save_screening(
    job_id,
    candidate_name,
    filename,
    resume_text,
    matched_skills,
    not_found_skills,
    match_percentage,
    ai_summary="",
):
    """Save a screening result for later review."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO screenings (
                job_id, candidate_name, filename, resume_text,
                matched_skills, not_found_skills, match_percentage,
                ai_summary
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                candidate_name,
                filename,
                resume_text,
                "\n".join(matched_skills),
                "\n".join(not_found_skills),
                float(match_percentage),
                ai_summary,
            ),
        )
        return cursor.lastrowid


def get_screenings(job_id=None):
    """Return screening records, optionally filtered by job."""
    with get_connection() as conn:
        if job_id is None:
            rows = conn.execute("""
                SELECT s.*, j.title AS job_title
                FROM screenings s
                JOIN jobs j ON s.job_id = j.id
                ORDER BY s.created_at DESC, s.id DESC
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT s.*, j.title AS job_title
                FROM screenings s
                JOIN jobs j ON s.job_id = j.id
                WHERE s.job_id = ?
                ORDER BY s.created_at DESC, s.id DESC
            """, (job_id,)).fetchall()

        return [dict(row) for row in rows]


def update_screening_status(screening_id, status):
    """Record a human review status."""
    allowed_statuses = {
        "Pending human review",
        "Reviewed",
        "Shortlist for interview",
        "Not proceeding",
    }

    if status not in allowed_statuses:
        raise ValueError("Invalid review status.")

    with get_connection() as conn:
        conn.execute(
            "UPDATE screenings SET status = ? WHERE id = ?",
            (status, screening_id),
        )
