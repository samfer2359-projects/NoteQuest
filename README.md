# NoteQuest — Local Setup Guide

## Prerequisites
- Python 3.10+
- PostgreSQL (running locally)
- Ollama with the `mistral` model
- Game images (see Step 5)

---

## Step 1 — Create the database

```bash
psql -U postgres -f database.sql
```

This creates the `notequest` database and all tables.

---

## Step 2 — Install Python dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

---

## Step 3 — Check your DB password

Open `app.py`, `m2.py`, and `question_generator.py`.
Each file has this block near the top — update to match your local Postgres:

```python
DB_CONFIG = {
    "database": "notequest",
    "user":     "postgres",
    "password": "root",       # ← change this if your password is different
    "host":     "localhost",
    "port":     "5432"
}
```

---

## Step 4 — Start Ollama

```bash
ollama serve          # starts the Ollama server
ollama pull mistral   # downloads the model (first time only, ~4 GB)
```

Ollama must be running at `http://localhost:11434` for question generation to work.

---

## Step 5 — Add game images

Place these 7 images inside `static/images/`:

| Filename           | What it looks like               |
|--------------------|----------------------------------|
| `stone-block.png`  | Gray stone tile (road)           |
| `water-block.png`  | Blue water tile (top row)        |
| `grass-block.png`  | Green grass tile (bottom rows)   |
| `enemy-bug.png`    | The bug enemy character          |
| `char-boy.png`     | Your player character            |
| `Star.png`         | Star decoration                  |
| `Gem Orange.png`   | Orange gem collectible           |

These are the standard Udacity Frogger assets — they're freely available online.
Search for "Udacity frontend nanodegree frogger assets" to find them.

---

## Step 6 — Run the app

```bash
python app.py
```

Open your browser at: **http://localhost:8000**

---

## Gameplay

1. Sign up and log in
2. Upload a `.txt`, `.docx`, or `.pdf` file from your DBMS notes on the Dashboard
3. Click **Play Now** to start the Frogger game
4. Use **arrow keys** to move your character
5. Avoid the bug enemies (you have 3 lives)
6. Collect the orange gem to trigger a quiz question
7. Answer correctly to earn points and advance levels

---

## Project Structure

```
notequest/
├── app.py                  ← Flask routes & auth
├── m2.py                   ← NLP concept extraction
├── question_generator.py   ← Ollama/Mistral AI questions
├── database.sql            ← PostgreSQL schema
├── requirements.txt
├── templates/
│   ├── welcome.html
│   ├── login.html
│   ├── signup.html
│   ├── dashboard.html
│   └── index.html          ← Frogger game page
├── static/
│   ├── css/style.css       ← Game page styles
│   ├── js/
│   │   ├── resources.js    ← Image loader
│   │   ├── app.js          ← Game entities & quiz logic
│   │   └── engine.js       ← Game loop & collision
│   └── images/             ← Place your 7 game images here
└── uploads/                ← Auto-created for note uploads
```
