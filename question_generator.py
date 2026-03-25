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



def connect_db():
    return psycopg2.connect(**DB_CONFIG)



def get_difficulty(level):
    if level <= 3:
        return 1
    elif level <= 6:
        return 2
    return 3



def get_user_concepts(user_id):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT concept_text FROM Concepts WHERE user_id=%s", (user_id,))
    concepts = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()
    return concepts



def get_unused_question(user_id, difficulty):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT q.question_id, q.riddle_text, q.options, q.correct_answer, q.hint
        FROM Questions q
        LEFT JOIN Progress p 
        ON q.question_id = p.question_id AND p.user_id = %s
        WHERE (p.solved IS NULL OR p.solved = FALSE)
        AND q.difficulty = %s
        AND q.source = 'db'
        ORDER BY RANDOM()
        LIMIT 1
    """, (user_id, difficulty))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "question_id": row[0],
        "question": row[1],
        "options": row[2] if row[2] else [],
        "correct_answer": row[3],
        "hint": row[4] or ""
    }



def get_any_question(difficulty, concept):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT question_id, riddle_text, options, correct_answer, hint
        FROM Questions
        WHERE difficulty = %s 
        AND concept = %s
        AND source = 'db'
        ORDER BY RANDOM()
        LIMIT 1
    """, (difficulty, concept))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "question_id": row[0],
        "question": row[1],
        "options": row[2] if row[2] else [],
        "correct_answer": row[3],
        "hint": row[4] or ""
    }



def mark_question_solved(user_id, question_id, score):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO Progress (user_id, question_id, solved, score_awarded)
        VALUES (%s,%s,TRUE,%s)
        ON CONFLICT (user_id, question_id)
        DO UPDATE SET solved=TRUE
    """, (user_id, question_id, score))

    conn.commit()
    cur.close()
    conn.close()



def store_question(data, difficulty, concept):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO Questions
        (topic, riddle_text, options, correct_answer, hint, difficulty, concept,source)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (riddle_text, topic) DO NOTHING
        RETURNING question_id
    """, (
        TOPIC,
        data["question"],
        json.dumps(data["options"]),
        data["correct_answer"],
        data["hint"],
        difficulty,
        concept,
        "llm"
    ))

    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return result[0] if result else None



def generate_llm_question(concept, difficulty):
    prompt = f"""
Generate a DBMS MCQ.
Concept: {concept}
Difficulty: {difficulty}

Return JSON:
{{
    "question": "...",
    "options": ["A","B","C","D"],
    "correct_answer": "...",
    "hint": "..."
}}
"""

    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )

        raw = resp.json().get("response", "")
        return manual_parse_json(raw)

    except Exception:
        return None


def manual_parse_json(raw):
    try:
        raw = raw.replace("'", '"')
        data = json.loads(raw)

        if (
            "question" in data and
            "options" in data and
            isinstance(data["options"], list) and
            len(data["options"]) == 4
        ):
            return data
    except Exception:
        return None

    return None





def fetch_question(level, user_id):
    difficulty = get_difficulty(level)

    
    concepts = get_user_concepts(user_id)

    if concepts:
        concept = random.choice(concepts)
        qdata = generate_llm_question(concept, difficulty)

        if qdata:
            qid = store_question(qdata, difficulty, concept)
            if qid:
                qdata["question_id"] = qid
                return qdata

    
    q = get_unused_question(user_id, difficulty)
    if q:
        return q

    
    if concepts:
        concept = random.choice(concepts)
        q = get_any_question(difficulty, concept)
        if q:
            return q

    return None