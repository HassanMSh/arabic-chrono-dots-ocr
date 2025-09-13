import sqlite3
from pathlib import Path
import json
from typing import List, Dict, Any, Optional

DB_PATH = Path("data/sqlite.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def insert_raw_result(pdf_path: str, slice_idx: int, result_json: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ocr_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pdf_path TEXT,
            slice_idx INTEGER,
            result_json TEXT
        )
    """)
    cur.execute(
        "INSERT INTO ocr_results (pdf_path, slice_idx, result_json) VALUES (?, ?, ?)",
        (pdf_path, slice_idx, result_json)
    )
    conn.commit()
    conn.close()


def insert_event(date: str, text: str, source_pdf: str, slice_idx: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            text TEXT,
            source_pdf TEXT,
            slice_idx INTEGER
        )
    """)
    cur.execute(
        "INSERT INTO events (date, text, source_pdf, slice_idx) VALUES (?, ?, ?, ?)",
        (date, text, source_pdf, slice_idx)
    )
    conn.commit()
    conn.close()

# -----------------
# QUERY FUNCTIONS
# -----------------

def get_events(from_date: Optional[str] = None, to_date: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT id, date, text, source_pdf, slice_idx FROM events WHERE 1=1"
    params = []

    if from_date:
        query += " AND date >= ?"
        params.append(from_date)

    if to_date:
        query += " AND date <= ?"
        params.append(to_date)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_event_by_id(event_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, date, text, source_pdf, slice_idx FROM events WHERE id=?", (event_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_event(event_id: int, new_text: str):
    """
    Allow manual correction of OCR text.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE events SET text=? WHERE id=?", (new_text, event_id))
    conn.commit()
    conn.close()
    
def clear_previous_results(pdf_path: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM ocr_results WHERE pdf_path=?", (pdf_path,))
    cur.execute("DELETE FROM events WHERE source_pdf=?", (pdf_path,))
    conn.commit()
    conn.close()