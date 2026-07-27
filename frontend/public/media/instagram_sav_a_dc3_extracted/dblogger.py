"""
Database logging module for gallery error tracking
"""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_LOG_PATH = Path("gallery_errors.db")

def init_error_db():
    """Initialize SQLite database for error logging"""
    conn = sqlite3.connect(DB_LOG_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS execution_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            step_name TEXT,
            status TEXT,
            message TEXT,
            details TEXT
        )
    ''')
    
    # Changed column name from 'exists' to 'file_exists' (SQL reserved word)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_validation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            folder_name TEXT,
            image_name TEXT,
            full_path TEXT,
            file_exists INTEGER,
            error_message TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS browser_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            error_type TEXT,
            error_message TEXT,
            source TEXT,
            lineno INTEGER,
            colno INTEGER,
            stack_trace TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS browser_console_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            log_level TEXT,
            message TEXT,
            source_info TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_load_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            image_url TEXT,
            success INTEGER,
            error_message TEXT,
            http_status INTEGER
        )
    ''')
    
    conn.commit()
    return conn

def log_step(conn, step_name, status, message, details=""):
    """Log a step to the database"""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO execution_log (timestamp, step_name, status, message, details)
        VALUES (?, ?, ?, ?, ?)
    ''', (datetime.now().isoformat(), step_name, status, message, details))
    conn.commit()
    print(f"[{step_name}] {status}: {message}")

def validate_image_path(conn, folder_name, image_name, base_path):
    """Validate that an image exists and log the result"""
    full_path = base_path / folder_name / image_name
    file_exists = full_path.exists()
    
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO image_validation (timestamp, folder_name, image_name, full_path, file_exists, error_message)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(),
        folder_name,
        image_name,
        str(full_path),
        1 if file_exists else 0,
        "" if file_exists else f"File not found: {full_path}"
    ))
    conn.commit()
    
    return file_exists

def extract_logs_from_db(conn):
    """Extract all logs from database and save to text files"""
    cursor = conn.cursor()
    
    # Extract execution logs
    cursor.execute("SELECT * FROM execution_log ORDER BY id")
    execution_logs = cursor.fetchall()
    
    with open('execution_log_export.txt', 'w') as f:
        f.write("=== EXECUTION LOGS ===\n")
        for log in execution_logs:
            f.write(f"{log[1]} | {log[2]} | {log[3]} | {log[4]} | {log[5]}\n")
    
    # Extract image validation logs
    cursor.execute("SELECT * FROM image_validation ORDER BY id")
    image_logs = cursor.fetchall()
    
    with open('image_validation_export.txt', 'w') as f:
        f.write("=== IMAGE VALIDATION LOGS ===\n")
        for log in image_logs:
            f.write(f"{log[1]} | {log[2]} | {log[3]} | EXISTS:{log[5]} | {log[6]}\n")
    
    # Count failed images
    cursor.execute("SELECT COUNT(*) FROM image_validation WHERE file_exists = 0")
    failed_count = cursor.fetchone()[0]
    
    print(f"\n=== LOG EXTRACTION COMPLETE ===")
    print(f"Execution logs: {len(execution_logs)} entries")
    print(f"Image validations: {len(image_logs)} entries")
    print(f"Failed images: {failed_count}")
    print(f"\nExported to:")
    print(f"  - execution_log_export.txt")
    print(f"  - image_validation_export.txt")
    print(f"  - gallery_errors.db (SQLite database)")
    
    return failed_count