import psycopg2
import random

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
    """Fetch all concepts from Concepts table."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT concept_text FROM Concepts")
    concepts = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return concepts


def store_question(question_data, level):
    """Store generated question in the Questions table."""
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




def get_related_concepts(correct, concepts, count=3):
    """Select random related concepts excluding the correct answer."""
    candidates = [c for c in concepts if c != correct]
    return random.sample(candidates, min(count, len(candidates)))


def create_riddle(correct, related, level):
    """Create question text and hint without revealing the answer."""
    if level <= 2:
        question_text = f"I am a core DBMS concept related to {related[0]}. Who am I?"
        hint_text = f"This concept is fundamental in DBMS."
    elif level <= 4:
        question_text = f"In a database, which concept helps manage {related[0]} effectively without breaking rules?"
        hint_text = f"It is connected to {related[0]}."
    elif level <= 6:
        question_text = f"After modifying {related[0]} in your database, which concept ensures consistency and reliability?"
        hint_text = f"Think about data integrity and DBMS rules."
    elif level <= 8:
        question_text = f"As a DB administrator, you need to handle {', '.join(related)} efficiently. Which concept ensures smooth operations?"
        hint_text = f"Focus on how DBMS components interact."
    else:
        question_text = f"You are designing a complex DBMS. To optimize performance and maintain {', '.join(related)}, which advanced concept would you use?"
        hint_text = f"Consider DBMS strategies and optimization."

    return question_text, hint_text


#MAIN QUESTION GENERATOR 

def generate_question(level):
    """Generate a riddle-style question based on uploaded concepts."""
    concepts = get_concepts()
    if not concepts:
        raise Exception("No concepts found. Upload notes first using m2.py")

    correct = random.choice(concepts)
    related = get_related_concepts(correct, concepts, min(3, len(concepts)-1))

    # Create question text and hint without revealing answer
    question_text, hint_text = create_riddle(correct, related, level)

    # Options: 1 correct + 3 distractors
    distractors = get_related_concepts(correct, concepts, 3)
    options = distractors + [correct]
    random.shuffle(options)

    question_data = {
        "question": question_text,
        "options": options,
        "correct_answer": correct,
        "hint": hint_text
    }

    # Store in DB
    store_question(question_data, level)

    return question_data