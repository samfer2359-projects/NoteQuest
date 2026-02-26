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


def get_concepts():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT concept_text FROM Concepts WHERE topic = %s", (TOPIC,))
    concepts = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return concepts


def store_question(question_data, level):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Questions
        (topic, riddle_text, options, correct_answer, hint, difficulty)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        TOPIC,
        question_data["question"],
        question_data["options"],
        question_data["correct_answer"],
        question_data["hint"],
        level
    ))

    conn.commit()
    cursor.close()
    conn.close()


#LLM INTEGRATION

def generate_llm_question(concept, level):
    prompt = f"""
    Generate a multiple choice question for a 2D educational treasure hunt game.

    Topic: DBMS
    Focus Concept: {concept}
    Difficulty Level: {level} (1 easy - 10 very hard)

    Rules:
    - 1 correct answer
    - 3 believable distractors
    - Clear but not obvious hint
    - Make difficulty realistic based on level
    - Output STRICT JSON only

    Format:
    {{
        "question": "...",
        "options": ["A", "B", "C", "D"],
        "correct_answer": "...",
        "hint": "..."
    }}
    """

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "mistral",
            "prompt": prompt,
            "stream": False
        }
    )

    result = response.json()["response"]

    try:
        parsed = json.loads(result)
        return parsed
    except:
        print("LLM returned invalid JSON")
        return None


#MAIN GENERATOR 

def generate_question(level):
    concepts = get_concepts()

    if not concepts:
        raise Exception("No concepts found. Upload notes first.")

    concept = random.choice(concepts)

    question_data = generate_llm_question(concept, level)

    if not question_data:
        raise Exception("LLM failed to generate question.")

    store_question(question_data, level)

    return question_data