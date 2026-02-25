from flask import Flask, request, jsonify
from flask_cors import CORS
from question_generator import generate_question

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "NoteQuest Backend Running"

@app.route("/generate-question", methods=["GET"])
def get_question():
    try:
        level = request.args.get("level", default=1, type=int)
        if level < 1: level = 1
        if level > 10: level = 10
        question = generate_question(level)
        return jsonify({
            "success": True,
            "level": level,
            "question": question
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)