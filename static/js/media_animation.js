class MediaAnimator {
    constructor() {
        this.mediaItems = [];
        this.currentIndex = 0;
        this.container = document.createElement('div');
        this.container.className = 'media-animation-container';
        this.transitionDuration = 100; // Reduced to 500ms
        this.isPlaying = true;
    }

    async initialize() {
        try {
            // Fetch media features from backend
            const response = await fetch('/api/media-features/');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('API Response:', data); // Debug log

            if (!data.media_features || !Array.isArray(data.media_features)) {
                throw new Error('Invalid media features data');
            }

            this.mediaItems = data.media_features;
            console.log('Media items loaded:', this.mediaItems.length); // Debug log

            // Only proceed if we have media items
            if (this.mediaItems.length > 0) {
                this.sortMediaByFeatures();
                this.createAnimationElements();
                this.startAnimation();
            } else {
                throw new Error('No media items found');
            }
        } catch (error) {
            console.error('Failed to initialize media animation:', error);
            this.container.innerHTML = `
                <div style="color: white; padding: 20px;">
                    Error loading media: ${error.message}
                </div>
            `;
            document.body.appendChild(this.container);
        }
    }

    sortMediaByFeatures() {
        // If no media items, return early
        if (this.mediaItems.length === 0) return;

        // Start with the first item
        const sorted = [this.mediaItems[0]];
        const remaining = this.mediaItems.slice(1);

        // Keep finding the most similar item until we've used all items
        while (remaining.length > 0) {
            const lastItem = sorted[sorted.length - 1];
            let nearestIndex = 0;
            let minDistance = Infinity;

            // Find the most similar remaining item
            for (let i = 0; i < remaining.length; i++) {
                if (!remaining[i].features || !lastItem.features) continue;
                
                const distance = this.calculateDistance(
                    remaining[i].features, 
                    lastItem.features
                );
                
                if (distance < minDistance) {
                    minDistance = distance;
                    nearestIndex = i;
                }
            }

            // Add the most similar item to sorted and remove from remaining
            sorted.push(remaining[nearestIndex]);
            remaining.splice(nearestIndex, 1);
        }

        this.mediaItems = sorted;
    }

    calculateDistance(features1, features2) {
        // Simple Euclidean distance between feature vectors
        if (!Array.isArray(features1) || !Array.isArray(features2)) return Infinity;
        
        return Math.sqrt(
            features1.reduce((sum, val, i) => {
                return sum + Math.pow((val - features2[i]), 2);
            }, 0)
        );
    }

    createAnimationElements() {
        this.container.innerHTML = `
            <div class="media-stage">
                <div class="current-media"></div>
                <div class="next-media"></div>
            </div>
            <button class="toggle-flow">Pause</button>
        `;

        document.body.appendChild(this.container);

        // Add pause/play toggle
        this.container.querySelector('.toggle-flow').addEventListener('click', () => {
            this.isPlaying = !this.isPlaying;
            this.container.querySelector('.toggle-flow').textContent = 
                this.isPlaying ? 'Pause' : 'Play';
            if (this.isPlaying) this.startAnimation();
        });
    }

    startAnimation() {
        if (!this.isPlaying) return;

        const currentElement = this.container.querySelector('.current-media');
        const nextElement = this.container.querySelector('.next-media');

        // Set up current media
        this.displayMedia(this.mediaItems[this.currentIndex], currentElement);
        
        // Set up next media
        const nextIndex = (this.currentIndex + 1) % this.mediaItems.length;
        this.displayMedia(this.mediaItems[nextIndex], nextElement);

        // Simple toggle without crossfade
        currentElement.style.display = 'flex';
        nextElement.style.display = 'none';

        setTimeout(() => {
            // Instant switch
            currentElement.style.display = 'none';
            nextElement.style.display = 'flex';

            // Move to next item
            this.currentIndex = nextIndex;

            // Queue up next transition immediately
            if (this.isPlaying) this.startAnimation();
            
        }, this.transitionDuration);
    }

    displayMedia(mediaItem, element) {
        if (!mediaItem) {
            console.error('Media item is undefined');
            return;
        }
        
        if (mediaItem.type === 'video') {
            element.innerHTML = `
                <video autoplay loop muted playsinline>
                    <source src="${mediaItem.url}" type="video/mp4">
                </video>
            `;
        } else {
            element.innerHTML = `<img src="${mediaItem.url}" alt="media">`;
        }
    }
}