"""Persistent daily equity baseline and kill-switch helpers."""
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from config import STATE_DB, KILL_SWITCH_FILE, MAX_DAILY_LOSS_FRACTION

def killed():
    return __import__("os").path.exists(KILL_SWITCH_FILE)

def daily_guard(equity):
    """Fail-closed daily drawdown guard based on marked account equity in quote asset."""
    day = datetime.now(timezone.utc).date().isoformat()
    db = sqlite3.connect(STATE_DB)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS daily_equity(day TEXT PRIMARY KEY, baseline TEXT NOT NULL)")
        row = db.execute("SELECT baseline FROM daily_equity WHERE day=?", (day,)).fetchone()
        if row is None:
            db.execute("INSERT INTO daily_equity(day,baseline) VALUES(?,?)", (day, str(equity)))
            db.commit()
            return True, Decimal("0"), Decimal("0")
        baseline = Decimal(row[0])
        if baseline <= 0: return False, Decimal("0"), baseline
        loss = max(Decimal("0"), (baseline - equity) / baseline)
        return loss < MAX_DAILY_LOSS_FRACTION, loss, baseline
    finally:
        db.close()
