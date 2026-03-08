import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from question_generator import fetch_question
import psycopg2
import subprocess
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session

# --- Folder paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'txt', 'docx', 'pdf'}

DB_CONFIG = {
    "database": "notequest",
    "user": "postgres",
    "password": "root",
    "host": "localhost",
    "port": "5432"
}

def connect_db():
    return psycopg2.connect(**DB_CONFIG)

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Flask App ---
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'notequest_secret_key'

# --- Helper ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Routes ---
@app.route("/")
def home():
    return render_template("welcome.html")

@app.route("/signup", methods=['GET','POST'])
def signup():

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            flash("Passwords do not match","error")
            return redirect(url_for('signup'))

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM Users WHERE email=%s",
            (email,)
        )

        user = cursor.fetchone()

        if user:
            flash("User already registered. Please login.","error")
            return redirect(url_for('login'))

        hashed = generate_password_hash(password)

        cursor.execute(
            "INSERT INTO Users(username,email,password) VALUES(%s,%s,%s)",
            (username,email,hashed)
        )

        conn.commit()
        cursor.close()
        conn.close()

        flash("Account created successfully!","success")
        return redirect(url_for('login'))

    return render_template("signup.html")

@app.route("/login", methods=['GET','POST'])
def login():

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, username, password, level, score FROM Users WHERE email=%s",
                (email,)
            )
            user = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        if not user:
            flash("No account found with this email. Please sign up first.", "error")
            return redirect(url_for('signup'))

        if not check_password_hash(user[2], password):
            flash("Incorrect password. Try again.", "error")
            return redirect(url_for('login'))

        # Successful login → set session
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['level'] = user[3]
        session['score'] = user[4]

        flash(f"Welcome back, {user[1]}!", "success")
        return redirect(url_for('dashboard'))

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        flash("You haven't signed up or logged in yet. Please sign up first!", "error")
        return redirect(url_for('signup'))

    user_data = {
        "username": session['username'],
        "level": session['level'],
        "score": session['score'],
        "riddle_preview": "Your next DBMS treasure awaits!"
    }

    return render_template("dashboard.html", **user_data)

@app.route("/update-progress", methods=['POST'])
def update_progress():
    data = request.get_json()
    user_id = data.get("user_id")
    level = data.get("level")
    score = data.get("score")

    if not user_id or level is None or score is None:
        return jsonify({"success": False, "error": "Missing data"}), 400

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Users SET level=%s, score=%s WHERE user_id=%s",
        (level, score, user_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

    # Update session to keep dashboard data in sync
    session['level'] = level
    session['score'] = score

    return jsonify({"success": True})

@app.route("/game")
def game():
    if 'user_id' not in session:
        flash("You need to log in to play the game.", "error")
        return redirect(url_for('login'))

    return render_template("game.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out successfully!", "success")
    return redirect(url_for('home'))

@app.route("/upload", methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file selected"}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({"success": False, "error": "Invalid file type"}), 400

        # Save file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Run concept extraction in a subprocess
        try:
            result = subprocess.run(
                ["python", os.path.join(BASE_DIR, "m2.py"), filepath, str(session['user_id'])],
                capture_output=True,
                text=True,
                check=True
            )
            print("m2.py output:", result.stdout)
        except subprocess.CalledProcessError as e:
            # Catch errors in m2.py
            return jsonify({
                "success": False,
                "error": f"Concept extraction failed: {e.stderr or e.stdout or 'Unknown error'}"
            }), 500

        # Pre-generate questions
        from question_generator import fetch_question
        total_levels = 10
        failed_levels = []

        for lvl in range(1, total_levels + 1):
            try:
                fetch_question(lvl, session['user_id'])
            except Exception as e:
                failed_levels.append(lvl)
                print(f"Failed to generate question for level {lvl}: {e}")

        response_message = f"Notes uploaded & questions generated for levels 1-{total_levels}."
        if failed_levels:
            response_message += f" Failed for levels: {failed_levels}"

        return jsonify({
            "success": True,
            "message": response_message,
            "total_levels": total_levels,
            "failed_levels": failed_levels
        })

    except Exception as e:
        # Catch any unexpected error
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/generate-question", methods=['GET'])
def get_question():
    try:
        level = request.args.get("level", default=1, type=int)
        level = max(1, min(level, 10))
        user_id = request.args.get("user_id", type=int) or session.get('user_id')

        from question_generator import fetch_question
        question = fetch_question(level, user_id)

        return jsonify({"success": True, "level": level, "question": question})
    except Exception as e:
        # Always return JSON on error
        return jsonify({"success": False, "error": str(e)}), 200

# --- Run ---
if __name__ == "__main__":
    app.run(debug=True, port=8000)