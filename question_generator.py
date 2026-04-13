import psycopg2
import random
import json
import os
from groq import Groq

# CONFIG 
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

TOPIC = "DBMS"

DB_CONFIG = {
    "database": "notequest",
    "user": "postgres",
    "password": "root",
    "host": "localhost",
    "port": "5432"
}

#  DB 
def connect_db():
    return psycopg2.connect(**DB_CONFIG)


def get_user_concepts(user_id):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT concept_text FROM Concepts WHERE user_id=%s",
        (user_id,)
    )

    concepts = [row[0] for row in cur.fetchall() if row[0]]

    cur.close()
    conn.close()

    return concepts


def get_difficulty(level):
    # safe scaling (you can later improve this)
    return max(1, min(level, 10))


#  GROQ 
def generate_groq_question(concept, difficulty):
    prompt = f"""
You are generating a DBMS multiple choice question.

Concept: {concept}
Difficulty: {difficulty}

STRICT RULES:
- 4 options only
- correct_answer must EXACTLY match one option
- no A/B/C/D labels
- no explanation text inside options

Return ONLY valid JSON:

{{
  "question": "string",
  "options": ["opt1", "opt2", "opt3", "opt4"],
  "correct_answer": "one of the options",
  "hint": "short helpful hint"
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        raw = response.choices[0].message.content.strip()
        return parse_json(raw)

    except Exception as e:
        print(" GROQ ERROR:", e)
        return None


def parse_json(raw):
    try:
        raw = raw.strip()

        # safer cleanup for LLM output
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()

        data = json.loads(raw)

        # validation 
        if (
            isinstance(data, dict)
            and "question" in data
            and isinstance(data.get("options"), list)
            and len(data["options"]) == 4
            and "correct_answer" in data
            and data["correct_answer"] in data["options"]
            and "hint" in data
        ):
            return data

    except Exception as e:
        print(" JSON PARSE ERROR:", e)

    return None


#  STORE 
def store_question(data, difficulty, concept):
    conn = connect_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO Questions
            (topic, riddle_text, options, correct_answer, hint, difficulty, concept, source)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (riddle_text, topic) DO NOTHING
            RETURNING question_id
        """, (
            TOPIC,
            data["question"],
            json.dumps(data["options"]),
            data["correct_answer"],
            data.get("hint", ""),
            difficulty,
            concept,
            "llm"
        ))

        row = cur.fetchone()
        conn.commit()

        return row[0] if row else None

    except Exception as e:
        print(" DB INSERT ERROR:", e)
        conn.rollback()
        return None

    finally:
        cur.close()
        conn.close()


#  FETCH HELPERS 
def normalize_question(row):
    options = row[2]

    if isinstance(options, str):
        options = json.loads(options)

    return {
        "question_id": row[0],
        "question": row[1],
        "options": options,
        "correct_answer": row[3],
        "hint": row[4] or "",
    }


def get_cached_llm_question(difficulty):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT question_id, riddle_text, options, correct_answer, hint
        FROM Questions
        WHERE source='llm'
        AND difficulty=%s
        ORDER BY RANDOM()
        LIMIT 1
    """, (difficulty,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    return normalize_question(row) if row else None


def get_db_question(difficulty):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT question_id, riddle_text, options, correct_answer, hint
        FROM Questions
        WHERE source='db'
        AND difficulty=%s
        ORDER BY RANDOM()
        LIMIT 1
    """, (difficulty,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    return normalize_question(row) if row else None


#  MAIN FLOW 
def fetch_question(level, user_id):
    difficulty = get_difficulty(level)
    concepts = get_user_concepts(user_id)

    # 1. TRY GENERATION
    if concepts:
        sampled = random.sample(concepts, min(3, len(concepts)))

        for concept in sampled:
            qdata = generate_groq_question(concept, difficulty)

            if qdata:
                qid = store_question(qdata, difficulty, concept)

                if qid:
                    qdata["question_id"] = qid
                    print(" GENERATED QUESTION")
                    return qdata

    # 2. CACHE FALLBACK
    cached = get_cached_llm_question(difficulty)
    if cached:
        print(" CACHE USED")
        return cached

    # 3. DB FALLBACK
    db_q = get_db_question(difficulty)
    if db_q:
        print(" DB FALLBACK USED")
        return db_q

    return None


#  PROGRESS 
def mark_question_solved(user_id, question_id, score):
    conn = connect_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO Progress (user_id, question_id, solved, score_awarded)
            VALUES (%s,%s,TRUE,%s)
            ON CONFLICT (user_id, question_id)
            DO UPDATE SET solved=TRUE
        """, (user_id, question_id, score))

        conn.commit()

    except Exception as e:
        print(" PROGRESS ERROR:", e)
        conn.rollback()

    finally:
        cur.close()
        conn.close()