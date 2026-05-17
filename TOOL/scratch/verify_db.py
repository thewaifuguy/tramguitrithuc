import sqlite3
import json

conn = sqlite3.connect("data/gced.db")
conn.row_factory = sqlite3.Row

print("Chapters:")
for row in conn.execute("SELECT id, topic, status FROM chapters"):
    print(f"ID: {row['id']}, Topic: {row['topic']}, Status: {row['status']}")

print("\nPosts:")
for row in conn.execute("SELECT id, chapter_id, type, status FROM posts"):
    print(f"ID: {row['id']}, ChapID: {row['chapter_id']}, Type: {row['type']}, Status: {row['status']}")

conn.close()
