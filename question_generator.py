

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



def get_user_concepts(user_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT concept_text FROM Concepts WHERE user_id=%s", (user_id,))
    concepts = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return concepts



def store_question(data, level, concept):
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO Questions
            (topic, riddle_text, options, correct_answer, hint, difficulty, concept)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (riddle_text, topic) DO NOTHING
        """, (
            TOPIC,
            data["question"],
            json.dumps(data["options"]),
            data["correct_answer"],
            data["hint"],
            level,
            concept
        ))
        conn.commit()
        cur.close()
        conn.close()
        print("[DB] Stored question:", data["question"])
    except Exception as e:
        print("[DB] Store question error:", e)



def generate_llm_question(concept, level, user_id):
    prompt = f"""
Generate a multiple choice question for a 2D educational treasure hunt game.
Topic: {TOPIC}
Focus Concept: {concept}
Difficulty Level: {level} (1 easy - 10 very hard)
Rules:
- 1 correct answer
- 3 plausible distractors
- Clear but not obvious hint
- Output in JSON

Format:
{{
"question": "...",
"options": ["A", "B", "C", "D"],
"correct_answer": "...",
"hint": "..."
}}
"""

    for attempt in range(MAX_LLM_RETRIES):
        try:
            resp = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "mistral", "prompt": prompt, "stream": False},
                timeout=120
            )
            raw = resp.json().get("response", "")
            
            parsed = manual_parse_json(raw)
            if parsed:
                print("[LLM] Generated question:", parsed["question"])
                return parsed
        except Exception as e:
            print(f"[LLM] Attempt {attempt+1} failed:", e)
            continue

    
    return generate_fallback_question(concept, user_id)



def manual_parse_json(raw_text):
    """
    Attempt to convert any LLM output into valid JSON.
    Handles:
    - single quotes
    - missing quotes around keys
    - simple manual fixes
    """
    try:
        
        cleaned = raw_text.replace("'", '"')
        
        cleaned = cleaned.replace("question:", '"question":') \
                         .replace("options:", '"options":') \
                         .replace("correct_answer:", '"correct_answer":') \
                         .replace("hint:", '"hint":')
        
        cleaned = cleaned.replace(",}", "}").replace(",]", "]")
        data = json.loads(cleaned)

        
        if all(k in data for k in ["question", "options", "correct_answer", "hint"]):
            if isinstance(data["options"], list) and len(data["options"]) == 4:
                if data["correct_answer"] in data["options"]:
                    return data
    except:
        pass
    return None



def generate_fallback_question(concept, user_id):
    all_concepts = get_user_concepts(user_id)
    distractors = [c for c in all_concepts if c != concept]
    distractors = random.sample(distractors, min(3, len(distractors)))
    while len(distractors) < 3:
        distractors.append("Something unrelated")

    options = [concept] + distractors
    random.shuffle(options)

    data = {
        "question": f"What best describes '{concept}'?",
        "options": options,
        "correct_answer": concept,
        "hint": f"Focus on the key idea of {concept}"
    }
    print("[FALLBACK] Generated question:", data["question"])
    return data



def generate_question(level, user_id):
    concepts = get_user_concepts(user_id)
    if not concepts:
        raise Exception("No concepts found. Upload notes first.")

    concept = random.choice(concepts)
    question_data = generate_llm_question(concept, level, user_id)
    store_question(question_data, level, concept)
    return question_data



fetch_question = generate_question



if __name__ == "__main__":
    q = generate_question(level=3, user_id=1)
    print(json.dumps(q, indent=2))