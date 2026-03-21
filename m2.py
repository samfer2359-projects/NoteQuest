
import os
import re
import psycopg2
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document
from PIL import Image
import pytesseract
from pdf2image import convert_from_path


DB_CONFIG = {
    "database": "notequest",
    "user": "postgres",
    "password": "root",
    "host": "localhost",
    "port": "5432"
}


def connect_db():
    """Establishes a connection to the PostgreSQL database."""
    return psycopg2.connect(**DB_CONFIG)


def extract_concepts_from_text(text: str) -> list:
    """
    Extracts short phrases (<= 8 words) or uppercase keywords as 'concepts'.
    Uppercase keywords are typical DBMS terms like SQL, ACID, JOIN.
    """
    concepts = set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        
        if len(line.split()) <= 8:
            concepts.add(line)
        
        uppercase_words = re.findall(r'\b[A-Z][A-Z0-9]{2,}\b', line)
        concepts.update(uppercase_words)
    return list(concepts)


def extract_text_from_file(file_path: str) -> str:
    """Extracts text from TXT, PDF, DOCX, and image files with OCR fallback."""
    ext = file_path.lower().split('.')[-1]

    if ext == "txt":
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    elif ext == "pdf":
        text = extract_pdf_text(file_path)
        if text.strip():
            return text
        
        text = ""
        pages = convert_from_path(file_path)
        for page in pages:
            text += pytesseract.image_to_string(page)
        return text

    elif ext == "docx":
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])

    elif ext in ["jpg", "jpeg", "png", "tiff"]:
        img = Image.open(file_path)
        return pytesseract.image_to_string(img)

    else:
        raise ValueError(f"Unsupported file type: {ext}")


def store_concepts(user_id: int, concepts: list):
    """Inserts unique concepts for a user into the Concepts table."""
    if not concepts:
        return
    conn = connect_db()
    cursor = conn.cursor()
    for concept in concepts:
        cursor.execute(
            "SELECT 1 FROM Concepts WHERE user_id=%s AND concept_text=%s",
            (user_id, concept)
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO Concepts (user_id, concept_text) VALUES (%s, %s)",
                (user_id, concept)
            )
    conn.commit()
    cursor.close()
    conn.close()


def process_uploaded_file(user_id: int, file_path: str) -> list:
    """
    Processes a file, extracts concepts, and stores them in the DB.
    Returns the list of extracted concepts.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    text = extract_text_from_file(file_path)
    concepts = extract_concepts_from_text(text)

    if not concepts:
        raise ValueError("No concepts could be extracted from the file.")

    store_concepts(user_id, concepts)
    return concepts


def safe_print(msg):
    """Print safely even on consoles that can't handle special characters."""
    try:
        print(msg)
    except Exception:
        print(''.join(c if ord(c) < 128 else '?' for c in msg))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        safe_print("Usage: python m2.py <file_path> <user_id>")
        sys.exit(1)

    file_path = sys.argv[1]
    user_id = int(sys.argv[2])

    try:
        concepts = process_uploaded_file(user_id, file_path)
        safe_print(f"Concepts extracted for user {user_id}: {len(concepts)} concepts")
        sys.exit(0)
    except Exception as e:
        safe_print(f"Concept extraction failed: {e}")
        sys.exit(1)