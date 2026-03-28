import os
import re
import psycopg2
import yake
from sklearn.feature_extraction.text import TfidfVectorizer
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
    return psycopg2.connect(**DB_CONFIG)



DBMS_KEYWORDS = {
    "sql", "dbms", "database", "normalization", "transaction",
    "acid", "join", "primary key", "foreign key", "index",
    "schema", "er diagram", "tuple", "relation", "attribute",
    "functional dependency", "locking", "deadlock",
    "concurrency", "isolation", "aggregation"
}



STOPWORDS = {"the", "is", "and", "of", "in", "to", "a", "for", "on", "with"}


def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return text


def clean_concept(concept: str) -> str:
    words = concept.lower().split()
    words = [w for w in words if w not in STOPWORDS]
    return " ".join(words).strip()



def extract_yake_keywords(text: str) -> set:
    kw_extractor = yake.KeywordExtractor(
        lan="en",
        n=3,
        dedupLim=0.9,
        top=40
    )

    keywords = kw_extractor.extract_keywords(text)
    return {kw for kw, score in keywords}



def extract_tfidf_keywords(text: str) -> set:
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=40,
        ngram_range=(1, 3)
    )

    try:
        tfidf_matrix = vectorizer.fit_transform([text])
        return set(vectorizer.get_feature_names_out())
    except:
        return set()



def is_dbms_related(concept: str) -> bool:
    for keyword in DBMS_KEYWORDS:
        if keyword in concept:
            return True
    return False



def extract_concepts_from_text(text: str) -> list:
    """
    Hybrid extraction:
    YAKE + TF-IDF + DBMS filtering + fallback rules
    """
    concepts = set()

    cleaned_text = clean_text(text)

    
    yake_keywords = extract_yake_keywords(cleaned_text)

    
    tfidf_keywords = extract_tfidf_keywords(cleaned_text)

    
    combined = yake_keywords.union(tfidf_keywords)

    for kw in combined:
        clean_kw = clean_concept(kw)

        if not clean_kw:
            continue

        
        if 2 <= len(clean_kw.split()) <= 4:
            if is_dbms_related(clean_kw):
                concepts.add(clean_kw)

    
    uppercase_words = re.findall(r'\b[A-Z][A-Z0-9]{2,}\b', text)
    concepts.update(uppercase_words)

    return list(concepts)



def extract_text_from_file(file_path: str) -> str:
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
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    text = extract_text_from_file(file_path)
    concepts = extract_concepts_from_text(text)

    if not concepts:
        raise ValueError("No concepts could be extracted.")

    store_concepts(user_id, concepts)
    return concepts



def safe_print(msg):
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
        safe_print(f"Extracted {len(concepts)} high-quality DBMS concepts")
        sys.exit(0)
    except Exception as e:
        safe_print(f"Concept extraction failed: {e}")
        sys.exit(1)