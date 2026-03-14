// ============================================================
//  NoteQuest — Game Entities & Quiz Logic
//  Depends on: resources.js  (loaded first)
//              engine.js     (loaded after this file)
// ============================================================

// ── Global game state ────────────────────────────────────────
let level      = 1;
let quizActive = false;
let totalGems  = 0;
let score      = 0;

// ── Enemy ────────────────────────────────────────────────────
class Enemy {
    constructor(x, y, speed) {
        this.x      = x;
        this.y      = y;
        this.speed  = speed;
        this.width  = 101;
        this.height = 171;
        this.sprite = '/static/images/enemy-bug.png';
    }

    update(dt) {
        this.x += this.speed * dt;
        if (this.x > 505) this.x = -101;
    }

    render() {
        const img = Resources.get(this.sprite);
        if (typeof drawSprite === 'function') {
            drawSprite(img, '#dc2626', '🐛 BUG', this.x, this.y, 60, 50);
        } else if (img) {
            ctx.drawImage(img, this.x, this.y);
        }
    }
}

// ── Player ───────────────────────────────────────────────────
class Player {
    constructor() {
        this.x      = 202;
        this.y      = 415;
        this.width  = 101;
        this.height = 171;
        this.lives  = 3;
        this.sprite = '/static/images/char-boy.png';
    }

    update() { /* movement handled by handleInput */ }

    render() {
        const img = Resources.get(this.sprite);
        if (typeof drawSprite === 'function') {
            drawSprite(img, '#2563eb', '🧙 YOU', this.x, this.y, 60, 50);
        } else if (img) {
            ctx.drawImage(img, this.x, this.y);
        }
    }

    handleInput(key) {
        if (quizActive || this.lives <= 0) return;

        const col = 101;
        const row = 83;

        if (key === 'left')  this.x = Math.max(0,   this.x - col);
        if (key === 'right') this.x = Math.min(404,  this.x + col);
        if (key === 'up')    this.y = Math.max(0,    this.y - row);
        if (key === 'down')  this.y = Math.min(415,  this.y + row);

        // Reached water row → advance level
        if (this.y < 50) {
            level++;
            this.x = 202;
            this.y = 415;
            spawnGem();
            scaleEnemies();
            updateUI();
            showLevelBanner(level);
        }
    }
}

// ── Gem / Treasure ───────────────────────────────────────────
class Gem {
    constructor() {
        this.width  = 60;   // smaller
        this.height = 60;   // smaller
        this.sprite = '/static/images/Gem Orange.png';
        this.setPosition(303, 83);
    }

    setPosition(x, y) { this.x = x; this.y = y; }

    render() {
        this.float = Math.sin(Date.now() / 300) * 5; // small float animation
        if (this.x < 0) return;   // hidden

        const img = Resources.get(this.sprite);
        if (typeof drawSprite === 'function') {
            // Draw smaller gem
            drawSprite(img, '#f59e0b', '💎', this.x + 20, this.y + 40 + this.float, 35, 35);
        } else if (img) {
            ctx.drawImage(img, this.x, this.y, 35, 35); // smaller size fallback
        }
    }
}

// ── Star (decorative) ────────────────────────────────────────
class Star {
    constructor(x, y) {
        this.x      = x;
        this.y      = y;
        this.width  = 101;
        this.height = 171;
        this.sprite = '/static/images/Star.png';
    }

    render() {
        const img = Resources.get(this.sprite);
        if (img) ctx.drawImage(img, this.x, this.y);
    }
}

// ── Initialise entities ──────────────────────────────────────
const allEnemies = [
    new Enemy(0,   60,  120),
    new Enemy(150, 143, 200),
    new Enemy(300, 226, 160),
];

const player   = new Player();
const gem1     = new Gem();
const allStars = [];

// ── UI helpers ───────────────────────────────────────────────
function updateUI() {
    document.getElementById('lives').textContent        = player.lives;
    document.getElementById('gems').textContent         = totalGems;
    document.getElementById('level-display').textContent = level;
    document.getElementById('score-display').textContent = score;
}

function showLevelBanner(lvl) {
    const banner = document.getElementById('levelBanner');
    banner.textContent = `⚔️  LEVEL ${lvl}  ⚔️`;
    banner.classList.add('show');
    setTimeout(() => banner.classList.remove('show'), 2000);
}

// ── Gem management ───────────────────────────────────────────
function spawnGem() {
    const cols = [0, 101, 202, 303, 404];
    const rows = [83, 166, 249];
    const x = cols[Math.floor(Math.random() * cols.length)];
    const y = rows[Math.floor(Math.random() * rows.length)];
    gem1.setPosition(x, y);
}

function scaleEnemies() {
    allEnemies.forEach(e => { e.speed *= 1.12; });
}

// ── Quiz: fetch question when gem collected ──────────────────
function onTreasureCollected(lvl) {
    showQuizLoading(true);
    fetch(`/generate-question?level=${lvl}&user_id=${window.USER_ID}`)
        .then(r => r.json())
        .then(data => {
            showQuizLoading(false);
            if (data.error) {
                showGameAlert('Quiz error: ' + data.error, 'error');
                quizActive = false;
                spawnGem();
                return;
            }
            showQuizModal(data);
        })
        .catch(err => {
            showQuizLoading(false);
            showGameAlert('Failed to load question: ' + err, 'error');
            quizActive = false;
            spawnGem();
        });
}

function showQuizLoading(on) {
    document.getElementById('quizLoading').style.display = on ? 'flex' : 'none';
}

// ── Build and show the quiz modal ────────────────────────────
function showQuizModal(data) {
    const modal = document.getElementById('quizModal');

    document.getElementById('quizQuestion').textContent = data.question;

    // Hint starts hidden — only revealed on wrong answer
    const hintEl = document.getElementById('quizHint');
    hintEl.textContent = data.hint ? `💡 Hint: ${data.hint}` : '';
    hintEl.classList.remove('hint-revealed');

    const container = document.getElementById('quizOptions');
    container.innerHTML = '';

    (data.options || []).forEach(opt => {

    const optionText = typeof opt === "object" ? opt.text : opt;

    const btn = document.createElement('button');
    btn.className = 'quiz-option';
    btn.textContent = optionText;

    btn.addEventListener('click', () =>
        handleAnswer(btn, optionText, data.correct_answer, data.hint)
    );

    container.appendChild(btn);
});

    modal.classList.add('active');
}

// ── Handle answer selection ───────────────────────────────────
function handleAnswer(btn, selected, correct, hint) {
    const allBtns = document.querySelectorAll('.quiz-option');
    allBtns.forEach(b => b.disabled = true);

    if (selected === correct) {
        // ── Correct ──────────────────────────────────────────
        btn.classList.add('correct');
        totalGems++;
        const pts = level * 100;
        score += pts;
        updateUI();

        // Persist to server
        fetch('/update-progress', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ user_id: window.USER_ID, level, score })
        });

        showGameAlert(`✅ Correct! +${pts} pts`, 'success');
        setTimeout(() => closeQuiz(), 1400);

    } else {
        // ── Wrong — show hint prominently ─────────────────────
        btn.classList.add('wrong');

        // Highlight the correct answer
        allBtns.forEach(b => {
            if (b.textContent === correct) b.classList.add('correct');
        });

        // Reveal the hint with animation
        const hintEl = document.getElementById('quizHint');
        if (hint) {
            hintEl.textContent = `💡 Hint: ${hint}`;
            hintEl.classList.add('hint-revealed');
        }

        // Status text
        document.getElementById('quizStatus').textContent = '❌ Wrong answer — study the hint!';
        document.getElementById('quizStatus').className   = 'quiz-status wrong-status';

        player.lives--;
        updateUI();

        // Keep modal open 3.5 s so user can read the hint, then close
        setTimeout(() => closeQuiz(), 3500);
    }
}

// ── Close modal and resume game ───────────────────────────────
function closeQuiz() {
    document.getElementById('quizModal').classList.remove('active');
    document.getElementById('quizStatus').textContent = '';
    quizActive = false;
    spawnGem();
    if (player.lives <= 0) {
        setTimeout(triggerGameOver, 200);
    }
}

// ── Game over ────────────────────────────────────────────────
function triggerGameOver() {
    document.getElementById('finalScore').textContent = score;
    document.getElementById('gameOverScreen').classList.add('active');
}

// ── HUD alert strip ──────────────────────────────────────────
function showGameAlert(msg, type) {
    const el = document.getElementById('gameAlert');
    el.textContent = msg;
    el.className   = `game-alert ${type} show`;
    clearTimeout(el._timer);
    el._timer = setTimeout(() => el.classList.remove('show'), 2800);
}

// ── Keyboard input ───────────────────────────────────────────
document.addEventListener('keyup', function(e) {
    const map = { ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up', ArrowDown: 'down' };
    if (map[e.key]) player.handleInput(map[e.key]);
});
