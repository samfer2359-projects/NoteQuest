import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from question_generator import fetch_question
import psycopg2
import subprocess
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session

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

def user_has_notes(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM Concepts WHERE user_id=%s LIMIT 1", (user_id,))
    exists = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return exists

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'notequest_secret_key'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home():
    return render_template("welcome.html")

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email    = request.form['email']
        password = request.form['password']
        confirm  = request.form['confirm_password']

        if password != confirm:
            flash("Passwords do not match", "error")
            return redirect(url_for('signup'))

        conn   = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user:
            flash("User already registered. Please login.", "error")
            cursor.close(); conn.close()
            return redirect(url_for('login'))

        hashed = generate_password_hash(password)
        cursor.execute("INSERT INTO Users(username,email,password) VALUES(%s,%s,%s)",
                       (username, email, hashed))
        conn.commit()
        cursor.close(); conn.close()

        flash("Account created successfully!", "success")
        return redirect(url_for('login'))

    return render_template("signup.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']

        try:
            conn   = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, username, password, level, score FROM Users WHERE email=%s",
                (email,))
            user = cursor.fetchone()
        finally:
            cursor.close(); conn.close()

        if not user:
            flash("No account found with this email. Please sign up first.", "error")
            return redirect(url_for('signup'))

        if not check_password_hash(user[2], password):
            flash("Incorrect password. Try again.", "error")
            return redirect(url_for('login'))

        session['user_id']  = user[0]
        session['username'] = user[1]
        session['level']    = user[3]
        session['score']    = user[4]

        flash(f"Welcome back, {user[1]}!", "success")
        return redirect(url_for('dashboard'))

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        flash("Please sign up or log in first!", "error")
        return redirect(url_for('signup'))

    return render_template("dashboard.html",
                           username=session['username'],
                           level=session['level'],
                           score=session['score'],
                           riddle_preview="Your next DBMS treasure awaits!")

@app.route("/update-progress", methods=['POST'])
def update_progress():
    data    = request.get_json()
    user_id = data.get("user_id")
    level   = data.get("level")
    score   = data.get("score")

    if not user_id or level is None or score is None:
        return jsonify({"success": False, "error": "Missing data"}), 400

    conn   = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE Users SET level=%s, score=%s WHERE user_id=%s",
                   (level, score, user_id))
    conn.commit()
    cursor.close(); conn.close()

    session['level'] = level
    session['score'] = score
    return jsonify({"success": True})

@app.route("/index")
def game():
    if 'user_id' not in session:
        flash("You need to log in to play the game.", "error")
        return redirect(url_for('login'))

    if not user_has_notes(session['user_id']):
        flash("Upload notes first to generate quiz questions!", "error")
        return redirect(url_for('dashboard'))

    return render_template("index.html", USER_ID=session['user_id'])

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

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            result = subprocess.run(
                ["python", os.path.join(BASE_DIR, "m2.py"), filepath, str(session['user_id'])],
                capture_output=True, text=True, check=True
            )
            print("m2.py output:", result.stdout)
        except subprocess.CalledProcessError as e:
            return jsonify({
                "success": False,
                "error": f"Concept extraction failed: {e.stderr or e.stdout or 'Unknown error'}"
            }), 500

        return jsonify({"success": True, "message": "Notes uploaded and concepts extracted successfully!"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/generate-question", methods=['GET'])
def get_question():
    try:
        level   = request.args.get("level", default=1, type=int)
        level   = max(1, min(level, 10))
        user_id = request.args.get("user_id", type=int) or session.get('user_id') or 1
        question = fetch_question(level, user_id)
        return jsonify(question)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 200

if __name__ == "__main__":
    app.run(debug=True, port=8000)
