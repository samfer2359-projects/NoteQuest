import os
import subprocess
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from question_generator import fetch_question, mark_question_solved

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx'}
MAX_LEVEL = 10

DB_CONFIG = {
    "database": "notequest",
    "user": "postgres",
    "password": "root",
    "host": "localhost",
    "port": "5432"
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

app.secret_key = 'notequest_secret_key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def connect_db():
    return psycopg2.connect(**DB_CONFIG)


def get_user_progress(user_id):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT level, score FROM Users WHERE user_id=%s", (user_id,))
    data = cur.fetchone()

    cur.close()
    conn.close()
    return data if data else (1, 0)


def update_user_progress(user_id, level, score):
    level = min(level, MAX_LEVEL)

    conn = connect_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE Users SET level=%s, score=%s WHERE user_id=%s",
        (level, score, user_id)
    )

    conn.commit()
    cur.close()
    conn.close()


def user_has_notes(user_id):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM Concepts WHERE user_id=%s LIMIT 1", (user_id,))
    exists = cur.fetchone() is not None

    cur.close()
    conn.close()
    return exists


#  ROUTES 
@app.route("/")
def home():
    return render_template("welcome.html")


@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    level, score = get_user_progress(user_id)

    return render_template(
        "dashboard.html",
        username=session['username'],
        level=level,
        score=score,
        user_has_notes=user_has_notes(user_id)
    )


@app.route("/game")
def game():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    if not user_has_notes(user_id):
        flash("Upload notes first!", "error")
        return redirect(url_for('dashboard'))

    level, score = get_user_progress(user_id)

    return render_template(
        "index.html",
        USER_ID=user_id,
        LEVEL=level,
        SCORE=score
    )


@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        # 1. required fields
        if not username or not email:
            flash("Username and Email are required", "error")
            return redirect(url_for('signup'))

        # 2. PASSWORD MUST EXIST 
        if not password or password.strip() == "":
            flash("Password is required", "error")
            return redirect(url_for('signup'))

        # 3. confirm password check
        if password != confirm:
            flash("Passwords do not match", "error")
            return redirect(url_for('signup'))

        # 4. weak password warning only 
        if len(password) < 6:
            flash("⚠️ Weak password, but account will still be created", "warning")

        conn = connect_db()
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM Users WHERE email=%s", (email,))
        if cur.fetchone():
            flash("User already exists", "error")
            cur.close()
            conn.close()
            return redirect(url_for('login'))

        hashed = generate_password_hash(password)

        cur.execute(
            "INSERT INTO Users(username,email,password,level,score) VALUES(%s,%s,%s,1,0)",
            (username, email, hashed)
        )

        conn.commit()
        cur.close()
        conn.close()

        flash("Signup successful!", "success")
        return redirect(url_for('login'))

    return render_template("signup.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password')

        # validation 
        if not email or not password:
            flash("Email and password are required", "error")
            return redirect(url_for('login'))

        conn = connect_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT user_id, username, password FROM Users WHERE email=%s",
            (email,)
        )
        user = cur.fetchone()

        cur.close()
        conn.close()

        if not user:
            flash("User not found", "error")
            return redirect(url_for('login'))

        if not check_password_hash(user[2], password):
            flash("Wrong password", "error")
            return redirect(url_for('login'))

        #  login success
        session['user_id'] = user[0]
        session['username'] = user[1]

        return redirect(url_for('dashboard'))


    return render_template("login.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email").strip()
        new_password = request.form.get("password")
        confirm = request.form.get("confirm_password")

        if not email or not new_password:
            flash("All fields are required", "error")
            return redirect(url_for("forgot_password"))

        if new_password != confirm:
            flash("Passwords do not match", "error")
            return redirect(url_for("forgot_password"))

        conn = connect_db()
        cur = conn.cursor()

        cur.execute("SELECT user_id FROM Users WHERE email=%s", (email,))
        user = cur.fetchone()

        if not user:
            flash("Email not registered", "error")
            cur.close()
            conn.close()
            return redirect(url_for("forgot_password"))

        hashed = generate_password_hash(new_password)

        cur.execute(
            "UPDATE Users SET password=%s WHERE email=%s",
            (hashed, email)
        )

        conn.commit()
        cur.close()
        conn.close()

        flash("Password updated successfully! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/generate-question")
def generate_question():
    try:
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({"error": "Not logged in"}), 401

        level, _ = get_user_progress(user_id)
        question = fetch_question(level, user_id)

        if not question:
            return jsonify({"error": "No questions available"})

        print(f"Question {question['question_id']} loaded")

        return jsonify(question)

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": "Internal server error"}), 500


@app.route("/submit-answer", methods=["POST"])
def submit_answer():
    data = request.get_json() or {}
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    question_id = data.get("question_id")
    selected_answer = data.get("answer")

    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT correct_answer
        FROM Questions
        WHERE question_id=%s
    """, (question_id,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Invalid question"}), 400

    correct_answer = row[0].strip()
    selected_answer = (selected_answer or "").strip()

    level, score = get_user_progress(user_id)

    #  CORRECT ANSWER PATH
    if selected_answer == correct_answer:
        score += 10

    
        if level >= MAX_LEVEL:
            game_completed = True
            new_level = MAX_LEVEL
        else:
            new_level = level + 1
            game_completed = False

        mark_question_solved(user_id, question_id, 10)
        update_user_progress(user_id, new_level, score)

        return jsonify({
            "correct": True,
            "score": score,
            "level": new_level,
            "game_completed": game_completed
        })

    #  WRONG ANSWER PATH
    if not data.get("used_hint"):
        return jsonify({
            "correct": False,
            "action": "hint",
            "hint": "Check the concept carefully."
        })

    return jsonify({
        "correct": False,
        "action": "restart",
        "score": score
    })


@app.route("/reset-progress", methods=["POST"])
def reset_progress():
    user_id = session.get("user_id")

    update_user_progress(user_id, 1, 0)

    conn = connect_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM Progress WHERE user_id=%s", (user_id,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"success": True})


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/upload", methods=['POST'])
def upload_file():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"success": False, "error": "Not logged in"}), 401

    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file selected"})

    file = request.files['file']

    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Invalid file"})

    filename = f"{user_id}_{secure_filename(file.filename)}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    file.save(filepath)

    try:
        import sys
        subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "m2.py"), filepath, str(user_id)],
            check=True
        )
    except subprocess.CalledProcessError:
        return jsonify({"success": False, "error": "Processing failed"})

    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(debug=True, port=8000)