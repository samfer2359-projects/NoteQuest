create database notequest;

\c notequest

CREATE TABLE Users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE,
    password VARCHAR(255) NOT NULL,
    level INT DEFAULT 1,
    score INT DEFAULT 0,
    badges TEXT[]
);

CREATE TABLE Questions (
    question_id SERIAL PRIMARY KEY,
    topic VARCHAR(100) NOT NULL,
    riddle_text TEXT NOT NULL,
    options TEXT[],
    correct_answer VARCHAR(255) NOT NULL,
    hint TEXT
);

CREATE TABLE Progress (
    progress_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    question_id INT NOT NULL,
    solved BOOLEAN DEFAULT FALSE,
    score_awarded INT DEFAULT 0,
    CONSTRAINT fk_user
        FOREIGN KEY(user_id) 
        REFERENCES Users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_question
        FOREIGN KEY(question_id)
        REFERENCES Questions(question_id)
        ON DELETE CASCADE,
    CONSTRAINT unique_user_question UNIQUE(user_id, question_id)
);

CREATE TABLE Notes (
    note_id SERIAL PRIMARY KEY,
    topic VARCHAR(100) NOT NULL,
    content TEXT NOT NULL
);

CREATE INDEX idx_users_username ON Users(username);
CREATE INDEX idx_questions_topic ON Questions(topic);
CREATE INDEX idx_progress_user ON Progress(user_id);
CREATE INDEX idx_progress_question ON Progress(question_id);

ALTER TABLE Questions
ADD COLUMN created_at TIMESTAMP DEFAULT NOW();

ALTER TABLE Questions
ADD COLUMN difficulty INT DEFAULT 1;

CREATE TABLE Concepts (
    concept_id SERIAL PRIMARY KEY,
    topic VARCHAR(100),
    concept_text TEXT
);