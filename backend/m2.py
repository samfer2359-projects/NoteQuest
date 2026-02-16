import sys
import os
import random
import string
import re
import spacy
import yake
import psycopg2
from docx import Document
from PyPDF2 import PdfReader
import fitz  # PyMuPDF
import easyocr
import numpy as np



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

print("Initializing EasyOCR...")
ocr_reader = easyocr.Reader(['en'])



def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"TXT file: extracted {len(content)} characters")
        return content

    elif ext == ".docx":
        doc = Document(file_path)
        content = "\n".join([para.text for para in doc.paragraphs])
        print(f"DOCX file: extracted {len(content)} characters")
        return content

    elif ext == ".pdf":
        text = ""
        with open(file_path, "rb") as f:
            reader = PdfReader(f)
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    print(f"PDF page {page_num + 1}: text extracted via PyPDF2")
                    text += page_text + "\n"
                else:
                    # Scanned or image-based PDF page
                    print(f"PDF page {page_num + 1}: scanned, running OCR via EasyOCR")
                    doc = fitz.open(file_path)
                    page_fitz = doc[page_num]
                    pix = page_fitz.get_pixmap()
                    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                    ocr_text = "\n".join(ocr_reader.readtext(img, detail=0))
                    print(f"OCR extracted {len(ocr_text)} characters")
                    text += ocr_text + "\n"
        return text

    else:
        raise ValueError("Only .txt, .docx, and .pdf files are supported.")


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



def generate_mcq(sentence, concept_pool):
    doc = nlp(sentence)

    noun_phrases = [
        chunk.text.strip().translate(str.maketrans('', '', string.punctuation))
        for chunk in doc.noun_chunks
        if len(chunk.text.strip()) > 3
    ]

    if not noun_phrases:
        return None

    correct_answer = None
    for np in noun_phrases:
        if np in concept_pool:
            correct_answer = np
            break
    if not correct_answer:
        correct_answer = noun_phrases[0]

    distractors = list(set(concept_pool) - {correct_answer})
    if len(distractors) < 3:
        return None
    distractors = random.sample(distractors, 3)
    options = distractors + [correct_answer]
    random.shuffle(options)

    # Replace the correct answer in the sentence with "I" (whole word, case-insensitive, only once)
    pattern = re.compile(r'\b' + re.escape(correct_answer) + r'\b', flags=re.IGNORECASE)
    riddle_text = f'"{pattern.sub("I", sentence, count=1)}" Who am I?'

    related = [np for np in noun_phrases if np != correct_answer]
    hint_text = related[0] if related else "This is a DBMS concept."
    hint = f"I am related to: {hint_text}"

    return {
        "riddle_text": riddle_text,
        "options": options,
        "correct_answer": correct_answer,
        "hint": hint
    }



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



def process_file(conn, content):
    sentences = preprocess(content)
    concept_pool = extract_keywords(content)

    for sentence in sentences:
        mcq = generate_mcq(sentence, concept_pool)
        if mcq:
            store_question(conn, mcq)

    print("Questions generated successfully.")


def main():
    if len(sys.argv) != 2:
        print("Usage: python module.py <file_path>")
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
