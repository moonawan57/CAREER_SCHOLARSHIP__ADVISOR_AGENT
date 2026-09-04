import sqlite3
conn = sqlite3.connect(r'c:\Users\A.C\Downloads\CAREER_SCHOLORSHIP_AGENT\backend\chats.db')
row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='chats'").fetchone()
print(row[0] if row else 'no table')
for r in conn.execute("PRAGMA table_info(chats)").fetchall():
    print(r)
