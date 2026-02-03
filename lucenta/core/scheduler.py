import sqlite3
import time
import json
import threading
import logging

class TaskRunner:
    def __init__(self, db_path: str = "lucenta_tasks.db"):
        self.db_path = db_path
        self._init_db()
        self.running = False

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT,
                    payload TEXT,
                    status TEXT DEFAULT 'PENDING',
                    scheduled_at REAL,
                    completed_at REAL,
                    result TEXT
                )
            """)

    def add_task(self, name: str, payload: dict, delay: int = 0):
        scheduled_at = time.time() + delay
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO tasks (task_name, payload, scheduled_at) VALUES (?, ?, ?)",
                (name, json.dumps(payload), scheduled_at)
            )
        logging.info(f"Task '{name}' scheduled for {scheduled_at}")

    def run(self):
        self.running = True
        logging.info("TaskRunner started.")
        while self.running:
            try:
                now = time.time()
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        "SELECT id, task_name, payload FROM tasks WHERE status = 'PENDING' AND scheduled_at <= ?",
                        (now,)
                    )
                    tasks = cursor.fetchall()

                    for tid, name, payload_str in tasks:
                        conn.execute("UPDATE tasks SET status = 'RUNNING' WHERE id = ?", (tid,))
                        payload = json.loads(payload_str)

                        logging.info(f"Executing task {name}: {payload}")

                        # In a real system, we'd have a registry of task handlers
                        # For Phase 1, we simulate success
                        result = f"Task {name} executed successfully at {time.time()}"

                        conn.execute(
                            "UPDATE tasks SET status = 'COMPLETED', completed_at = ?, result = ? WHERE id = ?",
                            (time.time(), result, tid)
                        )
            except Exception as e:
                logging.error(f"TaskRunner error: {e}")

            time.sleep(5)

    def start_background(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()

    def stop(self):
        self.running = False
