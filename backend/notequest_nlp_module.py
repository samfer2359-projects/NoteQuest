import sys
import random
import spacy
import yake
import psycopg2


# -----------------------------
# DATABASE CONFIGURATION
# -----------------------------
DB_CONFIG = {
    "database": "notequest",
    "user": "postgres",
    "password": "root",  
    "host": "localhost",
    "port": "5432"
}


# -----------------------------
# LOAD NLP MODEL
# -----------------------------
print("Loading NLP model...")
nlp = spacy.load("en_core_web_sm")


# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def connect_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("Connected to PostgreSQL database.")
        return conn
    except Exception as e:
        print("Database connection failed:", e)
        sys.exit(1)


# -----------------------------
# INSERT NOTE INTO DATABASE
# -----------------------------
def insert_note(conn, topic, content):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Notes (topic, content) VALUES (%s, %s)",
        (topic, content)
    )
    conn.commit()
    cursor.close()
    print("Note inserted into database.")


# -----------------------------
# FETCH NOTES
# -----------------------------
def fetch_notes(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT topic, content FROM Notes")
    notes = cursor.fetchall()
    cursor.close()
    return notes


# -----------------------------
# PREPROCESS TEXT
# -----------------------------
def preprocess(text):
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 10]


# -----------------------------
# KEYWORD EXTRACTION (YAKE)
# -----------------------------
def extract_keywords(text):
    kw_extractor = yake.KeywordExtractor(lan="en", n=2, top=30)
    keywords = kw_extractor.extract_keywords(text)
    return list(set([kw[0] for kw in keywords]))


# -----------------------------
# GENERATE MCQ + RIDDLE
# -----------------------------
def generate_mcq(sentence, concept_pool):

    doc = nlp(sentence)
    noun_phrases = [chunk.text for chunk in doc.noun_chunks]

    if not noun_phrases:
        return None

    correct_answer = noun_phrases[0]

    distractors = list(set(concept_pool) - {correct_answer})

    if len(distractors) < 3:
        return None

    distractors = random.sample(distractors, 3)

    options = distractors + [correct_answer]
    random.shuffle(options)

    riddle_text = f"""
I am a concept from database theory,
Hidden inside this technical story:
"{sentence}"
Who am I?
""".strip()

    hint = f"I am related to: {correct_answer}"

    return {
        "riddle_text": riddle_text,
        "options": options,
        "correct_answer": correct_answer,
        "hint": hint
    }


# -----------------------------
# STORE QUESTION
# -----------------------------
def store_question(conn, topic, mcq):
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Questions (topic, riddle_text, options, correct_answer, hint)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        topic,
        mcq["riddle_text"],
        mcq["options"],
        mcq["correct_answer"],
        mcq["hint"]
    ))

    conn.commit()
    cursor.close()


# -----------------------------
# PROCESS NOTES → GENERATE QUESTIONS
# -----------------------------
def process_notes(conn):
    notes = fetch_notes(conn)

    for topic, content in notes:

        print(f"\nProcessing topic: {topic}")

        sentences = preprocess(content)
        concept_pool = extract_keywords(content)

        for sentence in sentences:
            mcq = generate_mcq(sentence, concept_pool)

            if mcq:
                store_question(conn, topic, mcq)

        print("Questions generated for topic:", topic)


# -----------------------------
# MAIN FUNCTION
# -----------------------------
def main():

    if len(sys.argv) != 3:
        print("Usage: python notequest_nlp_module.py <file_path> <topic>")
        sys.exit(1)

    file_path = sys.argv[1]
    topic = sys.argv[2]

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print("Error reading file:", e)
        sys.exit(1)

    conn = connect_db()

    insert_note(conn, topic, content)
    process_notes(conn)

    conn.close()
    print("\nAll Done. Questions stored in database.")


if __name__ == "__main__":
    main()
