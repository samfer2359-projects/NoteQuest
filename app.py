import os
import subprocess
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from question_generator import fetch_question

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'docx'}  

DB_CONFIG = {
    "database": "notequest",
    "user": "postgres",
    "password": "root",
    "host": "localhost",
    "port": "5432"
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'notequest_secret_key'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB


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

@app.context_processor
def utility_processor():
    return dict(user_has_notes=user_has_notes)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def home():
    return render_template("welcome.html")

@app.route("/signup", methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for('signup'))

        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for('signup'))

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM Users WHERE email=%s", (email,))
        if cursor.fetchone():
            flash("User already exists. Login instead.", "error")
            cursor.close(); conn.close()
            return redirect(url_for('login'))

        hashed = generate_password_hash(password)
        cursor.execute("INSERT INTO Users(username,email,password,level,score) VALUES(%s,%s,%s,1,0)",
                       (username, email, hashed))
        conn.commit()
        cursor.close(); conn.close()
        flash("Account created successfully!", "success")
        return redirect(url_for('login'))
    return render_template("signup.html")

@app.route("/login", methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, password, level, score FROM Users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close(); conn.close()

        if not user:
            flash("No account found. Please sign up.", "error")
            return redirect(url_for('signup'))
        if not check_password_hash(user[2], password):
            flash("Incorrect password.", "error")
            return redirect(url_for('login'))

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
        flash("Please log in first!", "error")
        return redirect(url_for('login'))
    return render_template("dashboard.html",
                           username=session['username'],
                           level=session.get('level', 1),
                           score=session.get('score', 0),
                           has_notes=user_has_notes(session['user_id']))

@app.route("/game")
def game():
    if 'user_id' not in session:
        flash("You need to log in to play.", "error")
        return redirect(url_for('login'))
    if not user_has_notes(session['user_id']):
        flash("Upload notes first to generate quiz questions!", "error")
        return redirect(url_for('dashboard'))
    return render_template("index.html", USER_ID=session['user_id'])

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for("home"))


@app.route("/upload", methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file selected"}), 400
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Invalid file type. Only PDF, TXT, DOCX allowed"}), 400
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        result = subprocess.run(
            ["python", os.path.join(BASE_DIR, "m2.py"), filepath, str(session['user_id'])],
            capture_output=True, text=True, check=True
        )
        print("m2.py output:", result.stdout.strip())
    except subprocess.CalledProcessError as e:
        return jsonify({"success": False, "error": f"Concept extraction failed: {e.stderr or e.stdout}"}), 500

    return jsonify({"success": True, "message": "Notes uploaded and concepts extracted successfully!"})


@app.route("/generate-question", methods=['GET'])
def generate_question():
    try:
        question = fetch_question(session.get('level', 1), session.get('user_id'))
        return jsonify(question)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/submit-answer", methods=["POST"])
def submit_answer():
    data = request.get_json()
    user_id = session.get("user_id")
    selected = data.get("answer")
    correct = data.get("correct_answer")
    used_hint = data.get("used_hint", False)

    level = session.get("level", 1)
    score = session.get("score", 0)

    result = {}

    if selected == correct:
        points = 5 if used_hint else 10
        score += points
        level += 1
        result.update({"correct": True, "score": score, "level": level, "points": points, "level_up": True})
    else:
        
        if not used_hint:
            result.update({"correct": False, "action": "hint"})
        else:
            score -= 5
            result.update({"correct": False, "action": "restart", "score": score, "level_up": False})
            session['level'] = level  

   
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE Users SET score=%s, level=%s WHERE user_id=%s", (score, level, user_id))
    conn.commit()
    cursor.close()
    conn.close()

    session["score"] = score
    session["level"] = level

    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True, port=8000)