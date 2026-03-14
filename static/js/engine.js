
(function(global) {
    const doc    = global.document;
    const canvas = doc.getElementById('gameCanvas');
    const ctx    = canvas.getContext('2d');
    let lastTime;

    
    function main() {
        const now = Date.now();
        const dt  = (now - lastTime) / 1000.0;
        update(dt);
        render();
        lastTime = now;
        global.requestAnimationFrame(main);
    }

    function init() { lastTime = Date.now(); main(); }

    
    function update(dt) {
        allEnemies.forEach(e => e.update(dt));
        player.update();
        checkCollisions();
    }

    
    function checkCollisions() {
        if (quizActive || player.lives <= 0) return;

        const pBox = {
            x:      player.x + 15,
            y:      player.y + 60,
            width:  player.width  - 30,
            height: player.height - 80
        };

        
        allEnemies.forEach(e => {
            const eBox = { x: e.x + 15, y: e.y + 60, width: e.width - 30, height: e.height - 80 };
            if (overlaps(pBox, eBox)) {
                player.lives--;
                resetPlayerPosition();
                updateUI();
                showGameAlert(`🐛 Hit by a bug! Lives left: ${player.lives}`, 'error');
                if (player.lives <= 0) triggerGameOver();
            }
        });

        const gBox = { x: gem1.x + 20, y: gem1.y + 40, width: 35, height: 35 };
        if (overlaps(pBox, gBox)) {
            quizActive = true;
            gem1.setPosition(-200, -200);
            onTreasureCollected(level);
        }
    }

    function overlaps(a, b) {
        return a.x < b.x + b.width  &&
               a.x + a.width  > b.x &&
               a.y < b.y + b.height &&
               a.y + a.height > b.y;
    }

    
    const TILE_COLORS = {
        '/static/images/water-block.png': '#1e6fa8',
        '/static/images/stone-block.png': '#6b7280',
        '/static/images/grass-block.png': '#166534',
    };

    function drawTile(url, col, row) {
        const x = col * 101;
        const y = row * 83;
        const img = Resources.get(url);
        if (img) {
            ctx.drawImage(img, x, y);
        } else {
            
            ctx.fillStyle = TILE_COLORS[url] || '#334155';
            ctx.fillRect(x, y, 101, 83);
            
            ctx.strokeStyle = 'rgba(0,0,0,0.3)';
            ctx.lineWidth = 1;
            ctx.strokeRect(x, y, 101, 83);
        }
    }

    
    function render() {
        const rowImages = [
            '/static/images/water-block.png',
            '/static/images/stone-block.png',
            '/static/images/stone-block.png',
            '/static/images/stone-block.png',
            '/static/images/grass-block.png',
            '/static/images/grass-block.png'
        ];

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        for (let row = 0; row < 6; row++) {
            for (let col = 0; col < 5; col++) {
                drawTile(rowImages[row], col, row);
            }
        }

        renderEntities();
    }

    function renderEntities() {
        allStars.forEach(s => s.render());
        gem1.render();
        allEnemies.forEach(e => e.render());
        player.render();
    }

    
    function resetPlayerPosition() {
        player.x = 202;
        player.y = 415;
    }

    
    global.drawSprite = function(img, fallbackColor, label, x, y, w, h) {
        w = w || 60; h = h || 60;
        if (img) {
            ctx.drawImage(img, x, y);
        } else {
            
            ctx.fillStyle = fallbackColor;
            ctx.beginPath();
            ctx.roundRect ? ctx.roundRect(x + 20, y + 60, w, h, 8) : ctx.rect(x + 20, y + 60, w, h);
            ctx.fill();
            
            ctx.fillStyle = '#fff';
            ctx.font = 'bold 11px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(label, x + 20 + w / 2, y + 60 + h / 2 + 4);
            ctx.textAlign = 'left';
        }
    };

    
    Resources.load([
        '/static/images/stone-block.png',
        '/static/images/water-block.png',
        '/static/images/grass-block.png',
        '/static/images/enemy-bug.png',
        '/static/images/char-boy.png',
        '/static/images/Star.png',
        '/static/images/Gem Orange.png'
    ]);

    Resources.onReady(init);

    
    global.ctx = ctx;
})(this);
