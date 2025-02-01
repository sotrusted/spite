class Heart {
    constructor() {
        this.x = Math.random() * window.innerWidth;
        this.y = -10;
        this.size = Math.random() * 15 + 5; // Size between 5-20px
        this.speedY = Math.random() * 1 + 0.5; // Fall speed
        this.speedX = Math.random() * 2 - 1; // Sideways movement
        this.swing = Math.random() * 3; // Swinging amplitude
        this.phase = Math.random() * Math.PI * 2; // Random starting phase
    }

    update() {
        this.y += this.speedY;
        // Add gentle swinging motion
        this.x += Math.sin(this.y / 50 + this.phase) * this.swing * 0.1;
        this.x += this.speedX * 0.1;

        // Reset if heart goes off screen
        if (this.y > window.innerHeight) {
            this.y = -10;
            this.x = Math.random() * window.innerWidth;
        }
        if (this.x > window.innerWidth) {
            this.x = 0;
        }
        if (this.x < 0) {
            this.x = window.innerWidth;
        }
    }

    draw(ctx) {
        ctx.beginPath();
        const topCurveHeight = this.size * 0.3;
        
        // Draw heart shape
        ctx.moveTo(this.x, this.y + topCurveHeight);
        // Left curve
        ctx.bezierCurveTo(
            this.x - this.size/2, this.y, 
            this.x - this.size/2, this.y - this.size/2,
            this.x, this.y - this.size/2
        );
        // Right curve
        ctx.bezierCurveTo(
            this.x + this.size/2, this.y - this.size/2,
            this.x + this.size/2, this.y,
            this.x, this.y + topCurveHeight
        );
        
        ctx.fillStyle = 'rgba(255, 105, 180, 0.8)'; // Pink hearts
        ctx.fill();
    }
}

class HeartAnimation {
    constructor() {
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.hearts = [];
        this.isActive = false;
        
        // Style the canvas
        this.canvas.style.position = 'fixed';
        this.canvas.style.top = '0';
        this.canvas.style.left = '0';
        this.canvas.style.pointerEvents = 'none';
        this.canvas.style.zIndex = '1000';
        
        // Create toggle button
        this.toggleButton = document.createElement('button');
        this.toggleButton.innerHTML = '💝';
        this.toggleButton.className = 'heart-toggle';
        this.toggleButton.style.position = 'fixed';
        this.toggleButton.style.left = '10px';
        this.toggleButton.style.bottom = '10px';
        this.toggleButton.style.zIndex = '1001';
        this.toggleButton.style.padding = '8px';
        this.toggleButton.style.borderRadius = '50%';
        this.toggleButton.style.border = 'none';
        this.toggleButton.style.background = 'rgba(255, 255, 255, 0.7)';
        this.toggleButton.style.cursor = 'pointer';
        this.toggleButton.style.fontSize = '20px';
        
        // Add media query for mobile
        const mediaQuery = window.matchMedia('(max-width: 768px)');
        const adjustForMobile = (e) => {
            if (e.matches) {
                this.toggleButton.style.left = '10px';
                this.toggleButton.style.bottom = '60px'; // Move up to avoid clash with chat
                this.toggleButton.style.transform = 'scale(0.8)';
            } else {
                this.toggleButton.style.left = '10px';
                this.toggleButton.style.bottom = '10px';
                this.toggleButton.style.transform = 'scale(1)';
            }
        };
        mediaQuery.addListener(adjustForMobile);
        adjustForMobile(mediaQuery);
        
        this.init();
    }

    init() {
        // Add elements to DOM
        document.body.appendChild(this.canvas);
        document.body.appendChild(this.toggleButton);
        
        // Initialize hearts
        for (let i = 0; i < 50; i++) {
            this.hearts.push(new Heart());
        }
        
        // Event listeners
        this.toggleButton.addEventListener('click', () => this.toggle());
        window.addEventListener('resize', () => this.resize());
        
        // Initial resize
        this.resize();
        
        // Check localStorage for previous state, default to true if not set
        const savedState = localStorage.getItem('heartsEnabled');
        if (savedState === null || savedState === 'true') {
            this.start();
        }
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    toggle() {
        if (this.isActive) {
            this.stop();
        } else {
            this.start();
        }
    }

    start() {
        if (!this.isActive) {
            this.isActive = true;
            localStorage.setItem('heartsEnabled', 'true');
            this.animate();
            this.toggleButton.style.background = 'rgba(255, 192, 203, 0.7)';
        }
    }

    stop() {
        this.isActive = false;
        localStorage.setItem('heartsEnabled', 'false');
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.toggleButton.style.background = 'rgba(255, 255, 255, 0.7)';
    }

    animate() {
        if (!this.isActive) return;
        
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        this.hearts.forEach(heart => {
            heart.update();
            heart.draw(this.ctx);
        });
        
        requestAnimationFrame(() => this.animate());
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new HeartAnimation();
}); 