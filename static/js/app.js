let level = window.INIT_LEVEL || 1;
let score = window.INIT_SCORE || 0;
let totalGems = 0;
let quizActive = false;
let usedHint = false;
let currentQuestion = null;

const MAX_LEVEL = 10;

/*  ENEMIES  */

class Enemy {
    constructor(x, y, speed) {
        this.x = x;
        this.y = y;
        this.speed = speed;
        this.width = 101;
        this.height = 171;
        this.sprite = '/static/images/enemy-bug.png';
    }

    update(dt) {
        this.x += this.speed * dt;
        if (this.x > 505) this.x = -101;
    }

    render() {
        const img = Resources.get(this.sprite);
        if (img) ctx.drawImage(img, this.x, this.y);
    }
}

/*  PLAYER  */

class Player {
    constructor() {
        this.width = 101;
        this.height = 171;
        this.lives = 3;
        this.sprite = '/static/images/char-boy.png';
        this.reset();
    }

    reset() {
        this.x = 202;
        this.y = 415;
    }

    update() {}

    render() {
        const img = Resources.get(this.sprite);
        if (img) ctx.drawImage(img, this.x, this.y);
    }

    handleInput(key) {
        if (quizActive || this.lives <= 0) return;

        const col = 101;
        const row = 83;

        if (key === 'left') this.x = Math.max(0, this.x - col);
        if (key === 'right') this.x = Math.min(404, this.x + col);
        if (key === 'up') this.y = Math.max(0, this.y - row);
        if (key === 'down') this.y = Math.min(415, this.y + row);

        updateUI();
    }
}

/*  GEM  */

class Gem {
    constructor() {
        this.sprite = '/static/images/Gem_Orange.png';
        this.width = 35;
        this.height = 35;
        this.setPosition(-200, -200);
    }

    setPosition(x, y) {
        this.x = x;
        this.y = y;
    }

    render() {
        if (this.x < 0) return;

        const img = Resources.get(this.sprite);
        if (img) {
            const float = Math.sin(Date.now() / 300) * 5;
            ctx.drawImage(img, this.x, this.y + float, 35, 35);
        }
    }
}

/*  GAME OBJECTS  */

const allEnemies = [
    new Enemy(0, 143, 120),
    new Enemy(150, 226, 200),
    new Enemy(300, 309, 160)
];

const player = new Player();
const gem = new Gem();

/*  GAME LOGIC  */

function spawnGem() {
    const waterRows = [0, 1];
    const cols = [0, 101, 202, 303, 404];

    const row = waterRows[Math.floor(Math.random() * waterRows.length)];
    const x = cols[Math.floor(Math.random() * cols.length)];
    const y = row * 83 + 60;

    gem.setPosition(x, y);
}

function scaleEnemies() {
    allEnemies.forEach(e => e.speed *= 1.1);
}

/*  UI  */

function updateUI() {
    document.getElementById('lives').textContent = player.lives;
    document.getElementById('gems').textContent = totalGems;
    document.getElementById('level-display').textContent = level;
    document.getElementById('score-display').textContent = score;
}

function showGameAlert(msg, type) {
    const el = document.getElementById('gameAlert');
    el.textContent = msg;
    el.className = `game-alert ${type} show`;

    clearTimeout(el._timer);
    el._timer = setTimeout(() => el.classList.remove('show'), 2500);
}

function showQuizLoading(on) {
    document.getElementById('quizLoading').style.display = on ? 'flex' : 'none';
}

/*  QUIZ MODAL   */

function showQuizModal(data) {
    quizActive = true;

    const modal = document.getElementById('quizModal');
    const container = document.getElementById('quizOptions');

    document.getElementById('quizQuestion').textContent = data.question;
    container.innerHTML = "";

    let options = Array.isArray(data.options) ? [...data.options] : [];

    console.log(`Question ${data.question_id}`);
    console.log("Options:", options);

    options.forEach(opt => {
        const btn = document.createElement('button');
        btn.className = 'quiz-option';
        btn.textContent = opt;
        btn.onclick = () => submitAnswer(btn, opt);
        container.appendChild(btn);
    });

    document.getElementById('quizHint').textContent = "";
    document.getElementById('quizStatus').textContent = "";
    modal.classList.add('active');
}

/*  TREASURE FLOW  */

function onTreasureCollected() {
    usedHint = false;
    currentQuestion = null;

    showQuizLoading(true);

    fetch('/generate-question')
        .then(r => {
            if (!r.ok) throw new Error("Server error");
            return r.json();
        })
        .then(data => {
            showQuizLoading(false);

            if (data.error) {
                showGameAlert("Error loading question", "error");
                quizActive = false;
                spawnGem();
                return;
            }

            currentQuestion = data;
            showQuizModal(data);
        })
        .catch(() => {
            showQuizLoading(false);
            showGameAlert("Network error", "error");
        });
}

/*  ANSWERS  */

function submitAnswer(button, selected) {
    fetch("/submit-answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            answer: selected,
            used_hint: usedHint,
            question_id: currentQuestion.question_id
        })
    })
    .then(r => r.json())
    .then(res => {
        if (!res || res.error) {
            showGameAlert("Server error", "error");
            return;
        }
        handleAnswerResponse(button, res);
    });
}

function handleAnswerResponse(btn, res) {
    const hintEl = document.getElementById('quizHint');
    const statusEl = document.getElementById('quizStatus');

    if (res.correct) {
    
    btn.classList.add('correct');

    score = res.score;
    level = Math.min(res.level || level, MAX_LEVEL);
    totalGems++;

    updateUI();

    
    showGameAlert("✅ Correct answer! +10 points 🎉", "success");

    if (res.game_completed) {
        closeQuiz(true);
        showVictoryScreen();
        return;
    }

    closeQuiz(true);
    console.log("Level:", level, "Game Completed:", res.game_completed);
    return;
}

    
    btn.classList.add('wrong');

    if (res.action === "hint") {
        usedHint = true;

        hintEl.textContent = "💡 " + (currentQuestion?.hint || "");
        statusEl.textContent = "Try again using the hint!";
        statusEl.className = "quiz-status wrong-status";

        btn.disabled = true;
    } else if (res.action === "restart") {
        score = res.score;
        player.lives--;

        updateUI();

        showGameAlert("❌ Wrong again! Restarting level", "error");

        closeQuiz(false);
        resetLevel();

        if (player.lives <= 0) triggerGameOver();
    }
}


/* END SCREENS */

function showVictoryScreen() {
    document.getElementById('victoryScore').textContent = score;
    document.getElementById('victoryScreen').classList.add('active');
}

function triggerGameOver() {
    document.getElementById('finalScore').textContent = score;
    document.getElementById('gameOverScreen').classList.add('active');
}

/*  GAME STATE  */

function closeQuiz(success) {
    document.getElementById('quizModal').classList.remove('active');
    quizActive = false;

    if (success) {
        spawnGem();
    }

    player.reset();
}

function resetLevel() {
    player.reset();
    spawnGem();
    updateUI();
}

function restartGame() {
    fetch('/reset-progress', { method: 'POST' })
        .then(() => window.location.reload())
        .catch(() => alert("Failed to reset game"));
}

/*  INPUT  */

document.addEventListener('keyup', function (e) {
    const map = {
        ArrowLeft: 'left',
        ArrowRight: 'right',
        ArrowUp: 'up',
        ArrowDown: 'down'
    };

    if (map[e.key]) {
        player.handleInput(map[e.key]);
    }
});

/*  INIT  */

spawnGem();
updateUI();