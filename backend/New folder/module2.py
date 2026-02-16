import sys
import os
import random
import string
import spacy
import yake
import psycopg2
from docx import Document
from PyPDF2 import PdfReader

# =========================
# CONFIGURATION
# =========================

TOPIC = "DBMS"

DB_CONFIG = {
    "database": "notequest",
    "user": "postgres",
    "password": "root",
    "host": "localhost",
    "port": "5432"
}

print("Loading NLP model...")
nlp = spacy.load("en_core_web_sm")


# =========================
# FILE TEXT EXTRACTION
# =========================

def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    elif ext == ".docx":
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    elif ext == ".pdf":
        text = ""
        with open(file_path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    else:
        raise ValueError("Only .txt, .docx, and .pdf files are supported.")


# =========================
# DATABASE CONNECTION
# =========================

def connect_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("Connected to PostgreSQL database.")
        return conn
    except Exception as e:
        print("Database connection failed:", e)
        sys.exit(1)


def insert_note(conn, content):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Notes (topic, content) VALUES (%s, %s)",
        (TOPIC, content)
    )
    conn.commit()
    cursor.close()
    print("Note inserted into database.")


# =========================
# NLP PROCESSING
# =========================

def preprocess(text):
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 10]


def extract_keywords(text):
    kw_extractor = yake.KeywordExtractor(lan="en", n=2, top=30)
    keywords = kw_extractor.extract_keywords(text)

    clean_keywords = []
    for kw, _ in keywords:
        kw_clean = kw.strip().translate(str.maketrans('', '', string.punctuation))
        if len(kw_clean) > 3:
            clean_keywords.append(kw_clean)

    return list(set(clean_keywords))


# =========================
# MCQ GENERATION
# =========================

def generate_mcq(sentence, concept_pool):
    doc = nlp(sentence)

    noun_phrases = [
        chunk.text.strip().translate(str.maketrans('', '', string.punctuation))
        for chunk in doc.noun_chunks
        if len(chunk.text.strip()) > 3
    ]

    if not noun_phrases:
        return None

    # Select correct answer from concept pool if possible
    correct_answer = None
    for np in noun_phrases:
        if np in concept_pool:
            correct_answer = np
            break
    if not correct_answer:
        correct_answer = noun_phrases[0]

    # Generate distractors
    distractors = list(set(concept_pool) - {correct_answer})
    if len(distractors) < 3:
        return None
    distractors = random.sample(distractors, 3)
    options = distractors + [correct_answer]
    random.shuffle(options)

    # Riddle text: replace answer with "I" and keep "Who am I?" at the end
    riddle_text = f'"{sentence.replace(correct_answer, "I")}" Who am I?'

    # Hint: pick a related noun phrase (not the answer) or a generic hint
    related = [np for np in noun_phrases if np != correct_answer]
    hint_text = related[0] if related else "This is a DBMS concept."
    hint = f"I am related to: {hint_text}"

    return {
        "riddle_text": riddle_text,
        "options": options,
        "correct_answer": correct_answer,
        "hint": hint
    }


# =========================
# STORE QUESTIONS
# =========================

def store_question(conn, mcq):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Questions (topic, riddle_text, options, correct_answer, hint)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        TOPIC,
        mcq["riddle_text"],
        mcq["options"],
        mcq["correct_answer"],
        mcq["hint"]
    ))
    conn.commit()
    cursor.close()


# =========================
# MAIN PROCESSING PIPELINE
# =========================

def process_file(conn, content):
    sentences = preprocess(content)
    concept_pool = extract_keywords(content)

    for sentence in sentences:
        mcq = generate_mcq(sentence, concept_pool)
        if mcq:
            store_question(conn, mcq)

    print("Questions generated successfully.")


# =========================
# MAIN FUNCTION
# =========================

def main():
    if len(sys.argv) != 2:
        print("Usage: python module2.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        print("File not found.")
        sys.exit(1)

    try:
        content = extract_text(file_path)
        if not content.strip():
            raise ValueError("File contains no readable text.")
    except Exception as e:
        print("Error extracting file content:", e)
        sys.exit(1)

    conn = connect_db()
    insert_note(conn, content)
    process_file(conn, content)
    conn.close()

    print("\nAll Done. DBMS questions stored in database.")


if __name__ == "__main__":
    main()
