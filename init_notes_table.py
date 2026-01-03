#!/usr/bin/env python3
"""
Initialize or update the notes table in the database.
Run this if you already have a database and need to add the notes table.
"""

import sqlite3

DB_NAME = "cooperatives.db"

def init_notes_table():
    """Create the notes table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                listing_id INTEGER NOT NULL,
                FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        print("✓ Notes table created successfully!")
        
        # Check if table exists and show structure
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notes'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(notes)")
            columns = cursor.fetchall()
            print("\nNotes table structure:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
        
    except sqlite3.Error as e:
        print(f"Error creating notes table: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_notes_table()

