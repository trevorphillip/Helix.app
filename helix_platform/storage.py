import json, time, os, pathlib
DB = pathlib.Path(os.getenv("HLX_DB","helix.db.json"))

def load_db() -> dict:
    return json.loads(DB.read_text()) if DB.exists() else {"users":{}}

def save_db(data: dict) -> None:
    DB.write_text(json.dumps(data, indent=2))

def update_progress(user: str, card_id: str, grade: int) -> dict:
    # grade: 0..5; returns updated card state
    db = load_db()
    u = db["users"].setdefault(user, {"xp":0,"streak":0,"cards":{}})
    c = u["cards"].get(card_id, {"ease":2.5,"interval":0,"due":0,"reps":0})
    now = int(time.time())
    if grade < 3:
        c["interval"] = 1
    else:
        c["interval"] = max(1, int(c["interval"]*c["ease"])) or 1
        c["ease"] = max(1.3, c["ease"] + (0.1 if grade==5 else -0.08))
        u["xp"] += 10
    c["reps"] += 1
    c["due"] = now + c["interval"]*86400
    u["cards"][card_id] = c
    save_db(db)
    return c
