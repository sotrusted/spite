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
        ctx.save();
        ctx.translate(this.x, this.y);
        ctx.rotate(this.rotation * Math.PI / 180);
        
        // Draw shamrock (three heart-shaped leaves)
        ctx.fillStyle = this.color;
        
        // Draw three heart-shaped leaves that connect at the center
        for (let i = 0; i < 3; i++) {
            const angle = (i * Math.PI * 2 / 3);
            const leafX = Math.cos(angle) * (this.size * 0.3); // Reduced distance to center
            const leafY = Math.sin(angle) * (this.size * 0.3); // Reduced distance to center
            
            // Draw heart shape for each leaf
            ctx.save();
            ctx.translate(leafX, leafY);
            ctx.rotate(angle + Math.PI); // Rotate to point outward
            
            // Draw heart-shaped leaf
            const leafSize = this.size * 0.7; // Larger leaf size
            ctx.beginPath();
            ctx.moveTo(0, 0);
            // Left curve
            ctx.bezierCurveTo(
                -leafSize/2, -leafSize/4,
                -leafSize/2, -leafSize,
                0, -leafSize
            );
            // Right curve
            ctx.bezierCurveTo(
                leafSize/2, -leafSize,
                leafSize/2, -leafSize/4,
                0, 0
            );
            ctx.fill();
            ctx.restore();
        }
        
        // Draw a small circle in the center to connect the leaves
        ctx.beginPath();
        ctx.arc(0, 0, this.size * 0.15, 0, Math.PI * 2);
        ctx.fillStyle = this.color;
        ctx.fill();
        
        // Draw stem
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(0, this.size * 1.2);
        ctx.lineWidth = this.size / 10;
        ctx.strokeStyle = '#0D6B1E';
        ctx.stroke();
        
        ctx.restore();
    }

}

class Clover {
    constructor() {
        this.x = Math.random() * window.innerWidth;
        this.y = -10;
        this.size = Math.random() * 15 + 15; // Size between 15-30px
        this.speedY = Math.random() * 1 + 0.5; // Fall speed
        this.speedX = Math.random() * 2 - 1; // Sideways movement
        this.swing = Math.random() * 3; // Swinging amplitude
        this.phase = Math.random() * Math.PI * 2; // Random starting phase
        this.rotation = Math.random() * 360; // Random rotation
        this.color = Math.random() > 0.3 ? '#1D9E36' : '#0D8C24'; // Two shades of green
        this.symbol = '☘'; // Shamrock Unicode symbol
    }

    update() {
        this.y += this.speedY;
        // Add gentle swinging motion
        this.x += Math.sin(this.y / 50 + this.phase) * this.swing * 0.1;
        this.x += this.speedX * 0.1;
        this.rotation += 0.2; // Slowly rotate the clover

        // Reset if clover goes off screen
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
        ctx.save();
        ctx.translate(this.x, this.y);
        ctx.rotate(this.rotation * Math.PI / 180);
        
        // Set text properties
        ctx.font = `${this.size}px Arial`;
        ctx.fillStyle = this.color;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        // Draw the shamrock symbol
        ctx.fillText(this.symbol, 0, 0);
        
        ctx.restore();
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
        
        // Create button container for all fixed buttons
        this.buttonContainer = document.createElement('div');
        this.buttonContainer.className = 'fixed-button-container';
        this.buttonContainer.style.position = 'fixed';
        this.buttonContainer.style.left = '10px';
        this.buttonContainer.style.bottom = '10px';
        this.buttonContainer.style.zIndex = '1001';
        this.buttonContainer.style.display = 'flex';
        this.buttonContainer.style.flexDirection = 'column';
        this.buttonContainer.style.gap = '10px';
        
        // Create sound toggle button
        this.soundToggleButton = document.createElement('button');
        this.soundToggleButton.innerHTML = '🎵';
        this.soundToggleButton.className = 'sound-toggle fixed-button';
        this.soundToggleButton.style.padding = '8px';
        this.soundToggleButton.style.borderRadius = '50%';
        this.soundToggleButton.style.border = 'none';
        this.soundToggleButton.style.background = 'rgba(255, 255, 255, 0.7)';
        this.soundToggleButton.style.cursor = 'pointer';
        this.soundToggleButton.style.fontSize = '20px';
        
        // Create write button
        this.writeButton = document.createElement('button');
        this.writeButton.innerHTML = '✏️';
        this.writeButton.className = 'write-button fixed-button';
        this.writeButton.id = 'write-button';
        this.writeButton.style.padding = '8px';
        this.writeButton.style.borderRadius = '50%';
        this.writeButton.style.border = 'none';
        this.writeButton.style.background = 'rgba(255, 255, 255, 0.7)';
        this.writeButton.style.cursor = 'pointer';
        this.writeButton.style.fontSize = '20px';
        this.writeButton.addEventListener('click', function() {
            scrollToElementById('post-form');
        });

        // Add media query for mobile
        const mediaQuery = window.matchMedia('(max-width: 768px)');
        const adjustForMobile = (e) => {
            if (e.matches) {
                this.buttonContainer.style.left = '10px';
                this.buttonContainer.style.bottom = '60px'; // Move up to avoid clash with chat
                this.buttonContainer.style.transform = 'scale(0.8)';
            } else {
                this.buttonContainer.style.left = '10px';
                this.buttonContainer.style.bottom = '10px';
                this.buttonContainer.style.transform = 'scale(1)';
            }
        };
        mediaQuery.addEventListener('change', adjustForMobile);   
        
        this.init();
    }

    init() {
        // Add elements to DOM
        document.body.appendChild(this.canvas);

        // Add buttons to container
        this.buttonContainer.appendChild(this.soundToggleButton);
        this.buttonContainer.appendChild(this.writeButton);
        
        // Add container to DOM
        document.body.appendChild(this.buttonContainer);

        // Initialize hearts
        for (let i = 0; i < 50; i++) {
            this.hearts.push(new Clover());
        }
        
        // Event listeners
        window.addEventListener('resize', () => this.resize());
        
        // Sound toggle event listener
        this.soundToggleButton.addEventListener('click', () => this.toggleSound());

        // Write button event listener is set in the base.js file
        
        // Initial resize
        this.resize();
        
        // Check localStorage for previous state, default to true if not set
        const savedState = localStorage.getItem('heartsEnabled');
        if (savedState === null || savedState === 'true') {
            this.start();
        }

        // Check sound state
        const soundEnabled = localStorage.getItem('notificationSoundEnabled');
        if (soundEnabled === 'false') {
            this.soundToggleButton.innerHTML = '🔇';
            this.soundToggleButton.style.background = 'rgba(200, 200, 200, 0.7)';
        }
    }

    toggleSound() {
        const soundEnabled = localStorage.getItem('notificationSoundEnabled') !== 'false';
        localStorage.setItem('notificationSoundEnabled', !soundEnabled);
        
        if (soundEnabled) {
            // Sound is currently enabled, disable it
            this.soundToggleButton.innerHTML = '🔕';
            this.soundToggleButton.style.background = 'rgba(200, 200, 200, 0.7)';
        } else {
            // Sound is currently disabled, enable it
            this.soundToggleButton.innerHTML = '🎵';
            this.soundToggleButton.style.background = 'rgba(255, 255, 255, 0.7)';
        }
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    start() {
        if (!this.isActive) {
            this.isActive = true;
            localStorage.setItem('heartsEnabled', 'true');
            this.animate();
        }
    }

    stop() {
        this.isActive = false;
        localStorage.setItem('heartsEnabled', 'false');
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
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
//    new HeartAnimation();
}); 