import os
import sqlite3
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai

load_dotenv()
app = Flask(__name__)
DB = "chat_history.db"

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing in .env")

client = genai.Client(api_key=api_key)
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

SYSTEM_PROMPT = """
You are Mobile Expert. Answer ONLY mobile-phone related questions:
phones, specifications, processors, display, camera, battery, charging,
gaming, software/OS, updates, storage, RAM, 5G/4G, connectivity,
comparisons, troubleshooting, accessories, and phone buying guidance.
For unrelated questions, say you can answer only mobile-phone related questions.
"""

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    return conn

@app.route("/")
def home():
    db().close()
    return render_template("index.html")

@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"reply": "Please ask a mobile-phone related question."}), 400

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=SYSTEM_PROMPT + "\n\nUser question: " + message
        )
        answer = response.text or "No response received."
        conn = db()
        conn.execute("INSERT INTO history(question, answer) VALUES (?, ?)",
                     (message, answer))
        conn.commit()
        conn.close()
        return jsonify({"reply": answer})
    except Exception as e:
        return jsonify({"reply": "Gemini API error: " + str(e)}), 500

@app.get("/history")
def history():
    conn = db()
    rows = conn.execute(
        "SELECT id, question, answer, created_at FROM history ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.delete("/history/<int:item_id>")
def delete_history(item_id):
    conn = db()
    conn.execute("DELETE FROM history WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.delete("/history")
def clear_history():
    conn = db()
    conn.execute("DELETE FROM history")
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
