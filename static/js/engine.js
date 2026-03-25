(function(global){
    const doc = global.document;
    const canvas = doc.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');
    let lastTime;

    function main(){
        const now = Date.now();
        const dt = (now-lastTime)/1000.0;
        update(dt);
        render();
        lastTime = now;
        global.requestAnimationFrame(main);
    }

    function init(){ lastTime=Date.now(); main(); }

    function update(dt){
        allEnemies.forEach(e=>e.update(dt));
        player.update();
        checkCollisions();
    }

    function checkCollisions(){
        if(quizActive || player.lives<=0) return;

        const pBox = {x:player.x+15, y:player.y+60, width:player.width-30, height:player.height-80};

        
        if(player.y >= 2*83 && player.y <= 4*83){
            allEnemies.forEach(e=>{
                const eBox = {x:e.x+15, y:e.y+60, width:e.width-30, height:e.height-80};
                if(overlaps(pBox,eBox)){
                    player.lives--;
                    player.reset();
                    updateUI();
                    showGameAlert(`🐛 Hit by a bug! Lives left: ${player.lives}`,'error');
                    if(player.lives<=0) triggerGameOver();
                }
            });
        }

        
        const gBox = {x:gem.x, y:gem.y, width:gem.width, height:gem.height};
        if(overlaps(pBox,gBox)){
            gem.setPosition(-200,-200);
            onTreasureCollected();
        }
    }

    function overlaps(a,b){
        return a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y;
    }

    const TILE_COLORS={'/static/images/water-block.png':'#1e6fa8','/static/images/stone-block.png':'#6b7280','/static/images/grass-block.png':'#166534'};

    function drawTile(url,col,row){
        const x=col*101, y=row*83, img=Resources.get(url);
        if(img) ctx.drawImage(img,x,y);
        else { ctx.fillStyle=TILE_COLORS[url]||'#334155'; ctx.fillRect(x,y,101,83); ctx.strokeStyle='rgba(0,0,0,0.3)'; ctx.strokeRect(x,y,101,83); }
    }

    function render(){
        const rowImages=[
            '/static/images/water-block.png', // row 0
            '/static/images/water-block.png', // row 1
            '/static/images/stone-block.png', // row 2
            '/static/images/stone-block.png', // row 3
            '/static/images/stone-block.png', // row 4
            '/static/images/grass-block.png'  // row 5 
        ];
        ctx.clearRect(0,0,canvas.width,canvas.height);
        for(let row=0; row<6; row++) 
            for(let col=0; col<5; col++) 
                drawTile(rowImages[row], col, row);
        renderEntities();
    }

    function renderEntities(){
        allEnemies.forEach(e=>e.render());
        gem.render();   
        player.render();
    }

    Resources.load([
        '/static/images/stone-block.png',
        '/static/images/water-block.png',
        '/static/images/grass-block.png',
        '/static/images/enemy-bug.png',
        '/static/images/char-boy.png',
        '/static/images/Gem_Orange.png'
    ]);

    Resources.onReady(init);
    global.ctx=ctx;
})(this);