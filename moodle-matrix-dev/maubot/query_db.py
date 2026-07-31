import sqlite3
db = sqlite3.connect('/data/maubot.db')
tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables:", tables)

try:
    db.execute("UPDATE instance SET enabled=1 WHERE id='llm-wiki-assistant'")
    db.commit()
    print("Instances:", db.execute("SELECT * FROM instance").fetchall())
except Exception as e:
    print(e)
    print(e)
