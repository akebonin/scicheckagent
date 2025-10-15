# database.py
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATABASE_NAME = 'scicheck_cache.db'

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # Main analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                mode TEXT NOT NULL,
                use_papers INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Claims table linked to an analysis
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id TEXT NOT NULL,
                claim_text TEXT NOT NULL,
                model_verdict_json TEXT,
                questions_json TEXT,
                search_keywords_json TEXT,
                external_verdict TEXT,
                sources_json TEXT,
                reports_json TEXT,
                FOREIGN KEY (analysis_id) REFERENCES analyses (id)
            )
        ''')

        conn.commit()
        conn.close()
        logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database error during initialization: {e}")

if __name__ == '__main__':
    init_db()

