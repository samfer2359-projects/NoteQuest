import psycopg2
import random
import requests
import json

TOPIC = "DBMS"

DB_CONFIG = {
    "database": "notequest",
    "user": "postgres",
    "password": "root",
    "host": "localhost",
    "port": "5432"
}

MAX_LLM_RETRIES = 3


def connect_db():
    return psycopg2.connect(**DB_CONFIG)


def get_concepts(user_id):
    conn   = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT concept_text FROM Concepts WHERE user_id=%s", (user_id,))
    concepts = [row[0] for row in cursor.fetchall()]
    cursor.close(); conn.close()
    return concepts


def question_exists(question_text):
    conn   = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM Questions WHERE riddle_text=%s AND topic=%s", (question_text, TOPIC))
    exists = cursor.fetchone() is not None
    cursor.close(); conn.close()
    return exists


def store_question(question_data, level):
    if question_exists(question_data["question"]):
        return

    conn   = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Questions (topic, riddle_text, options, correct_answer, hint, difficulty)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        TOPIC,
        question_data["question"],
        json.dumps(question_data["options"]),
        question_data["correct_answer"],
        question_data["hint"],
        level
    ))
    conn.commit()
    cursor.close(); conn.close()


def sanitize_llm_output(text):
    try:
        return json.loads(text)
    except Exception:
        text = text.replace("\u201c", '"').replace("\u201d", '"').replace("\n", "")
        text = text.replace(",}", "}").replace(",]", "]")
        try:
            return json.loads(text)
        except Exception:
            return None


def generate_llm_question(concept, level):
    if level <= 3:
        diff_text    = "Easy"
        instructions = "Simple recall or definition. Clear and concise."
    elif level <= 7:
        diff_text    = "Medium"
        instructions = "Scenario-based application of the concept. Avoid trivial CRUD examples."
    else:
        diff_text    = "Hard"
        instructions = "Complex multi-step scenario. Requires reasoning and deduction."

    prompt = f"""
    Generate a multiple-choice question for a 2D educational treasure hunt.
    Topic: {TOPIC}
    Concept: {concept}
    Difficulty: {level} ({diff_text})
    Instructions:
    - {instructions}
    - 1 correct answer, 3 plausible distractors
    - Include a subtle hint
    - Be creative and realistic
    STRICT JSON ONLY: keys must be: question, options, correct_answer, hint
    """

    for attempt in range(MAX_LLM_RETRIES):
        try:
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "mistral", "prompt": prompt, "stream": False},
                timeout=None
            )
            text   = resp.json().get("response", "")
            parsed = sanitize_llm_output(text)
            if parsed and all(k in parsed for k in ["question", "options", "correct_answer", "hint"]):
                if isinstance(parsed["options"], str):
                    parsed["options"] = json.loads(parsed["options"])
                return parsed
        except Exception as e:
            print(f"LLM attempt {attempt+1} failed: {e}")

    raise Exception(f"Failed to generate question for concept: {concept}, level: {level}")


def fetch_question(level, user_id):
    conn   = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT q.question_id, q.riddle_text, q.options, q.correct_answer, q.hint
        FROM Questions q
        WHERE q.difficulty=%s AND q.topic=%s
          AND q.question_id NOT IN (
              SELECT question_id FROM UserQuestionProgress WHERE user_id=%s
          )
        ORDER BY question_id
        LIMIT 1
    """, (level, TOPIC, user_id))

    row = cursor.fetchone()

    if row:
        question_id, riddle_text, options, correct_answer, hint = row
    else:
        concepts = get_concepts(user_id)
        if not concepts:
            cursor.close(); conn.close()
            raise Exception("No concepts found. Upload notes first!")

        concept   = random.choice(concepts)
        generated = generate_llm_question(concept, level)
        store_question(generated, level)

        cursor.execute("""
            SELECT question_id, riddle_text, options, correct_answer, hint
            FROM Questions WHERE riddle_text=%s AND topic=%s
        """, (generated["question"], TOPIC))
        row = cursor.fetchone()
        question_id, riddle_text, options, correct_answer, hint = row

    cursor.execute("""
        INSERT INTO UserQuestionProgress(user_id, question_id, level)
        VALUES (%s,%s,%s)
        ON CONFLICT (user_id, question_id) DO NOTHING
    """, (user_id, question_id, level))

    conn.commit()
    cursor.close(); conn.close()

    return {
        "question_id":    question_id,
        "question":       riddle_text,
        "options":        json.loads(options) if isinstance(options, str) else options,
        "correct_answer": correct_answer,
        "hint":           hint
    }
