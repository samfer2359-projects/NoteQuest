from flask import Flask, request, jsonify, session
import psycopg2
import random
from flask_cors import CORS

# -----------------------------
# DATABASE CONFIGURATION
# -----------------------------
DB_CONFIG = {
    "database": "notequest",
    "user": "postgres",
    "password": "root",  # CHANGE THIS
    "host": "localhost",
    "port": "5432"
}

# -----------------------------
# FLASK APP SETUP
# -----------------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"  # For sessions if needed
CORS(app)  # Allows cross-origin requests from frontend

# -----------------------------
# DATABASE CONNECTION HELPER
# -----------------------------
def get_conn():
    return psycopg2.connect(**DB_CONFIG)

# -----------------------------
# SIGN UP
# -----------------------------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")  # In production, hash this!

    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Users (username, email, password)
            VALUES (%s, %s, %s) RETURNING user_id
        """, (username, email, password))
        user_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "user_id": user_id})
    except psycopg2.errors.UniqueViolation:
        return jsonify({"success": False, "error": "Username or email already exists"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, password FROM Users WHERE username=%s", (username,))
        row = cursor.fetchone()
        conn.close()

        if row and row[1] == password:
            return jsonify({"success": True, "user_id": row[0], "username": username})
        else:
            return jsonify({"success": False, "error": "Invalid username or password"}), 401
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# -----------------------------
# GET RANDOM QUESTION
# -----------------------------
@app.route("/get_question", methods=["GET"])
def get_question():
    user_id = request.args.get("user_id")
    try:
        conn = get_conn()
        cursor = conn.cursor()

        # Fetch questions the user has not solved yet
        cursor.execute("""
            SELECT q.question_id, q.riddle_text, q.options, q.correct_answer, q.hint
            FROM Questions q
            LEFT JOIN Progress p
            ON q.question_id = p.question_id AND p.user_id = %s
            WHERE p.solved IS NULL OR p.solved = FALSE
            ORDER BY random() LIMIT 1
        """, (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            question = {
                "question_id": row[0],
                "riddle": row[1],
                "options": row[2],
                "correct_answer": row[3],
                "hint": row[4]
            }
            return jsonify({"success": True, "question": question})
        else:
            return jsonify({"success": False, "message": "No unsolved questions available"}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# -----------------------------
# SUBMIT ANSWER
# -----------------------------
@app.route("/submit_answer", methods=["POST"])
def submit_answer():
    data = request.json
    user_id = data.get("user_id")
    question_id = data.get("question_id")
    answer = data.get("answer")

    try:
        conn = get_conn()
        cursor = conn.cursor()

        # Get correct answer
        cursor.execute("SELECT correct_answer FROM Questions WHERE question_id=%s", (question_id,))
        correct_answer = cursor.fetchone()[0]

        is_correct = (answer == correct_answer)
        score_awarded = 10 if is_correct else 0

        # Insert/update progress
        cursor.execute("""
            INSERT INTO Progress (user_id, question_id, solved, score_awarded)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, question_id) DO UPDATE
            SET solved = EXCLUDED.solved,
                score_awarded = EXCLUDED.score_awarded
        """, (user_id, question_id, is_correct, score_awarded))

        # Update user score
        cursor.execute("""
            UPDATE Users SET score = score + %s WHERE user_id = %s
        """, (score_awarded, user_id))

        conn.commit()
        conn.close()

        return jsonify({"success": True, "correct": is_correct, "score_awarded": score_awarded})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# -----------------------------
# GET USER INFO (optional)
# -----------------------------
@app.route("/user_info", methods=["GET"])
def user_info():
    user_id = request.args.get("user_id")
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT username, level, score, badges FROM Users WHERE user_id=%s", (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({
                "success": True,
                "username": row[0],
                "level": row[1],
                "score": row[2],
                "badges": row[3]
            })
        else:
            return jsonify({"success": False, "message": "User not found"}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
