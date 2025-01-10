class MediaAnimator {
    constructor() {
        this.mediaItems = [];
        this.currentIndex = 0;
        this.container = document.createElement('div');
        this.container.className = 'media-animation-container';
        this.transitionDuration = 500;
        this.isPlaying = true;
        console.log('MediaAnimator initialized');
    }

    async initialize() {
        try {
            const response = await fetch('/api/media-features/');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('API Response:', data);

            this.mediaItems = data.media_features;
            console.log('Media items loaded:', this.mediaItems.length);

            if (this.mediaItems.length > 0) {
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

    createAnimationElements() {
        console.log('Creating animation elements');
        this.container.innerHTML = `
            <div class="media-stage">
                <div class="current-media"></div>
                <div class="next-media"></div>
            </div>
            <button class="toggle-flow">Pause</button>
        `;

        document.body.appendChild(this.container);

        const toggleButton = this.container.querySelector('.toggle-flow');
        toggleButton.addEventListener('click', () => {
            this.isPlaying = !this.isPlaying;
            toggleButton.textContent = this.isPlaying ? 'Pause' : 'Play';
            console.log('Animation:', this.isPlaying ? 'playing' : 'paused');
            if (this.isPlaying) this.startAnimation();
        });
    }

    startAnimation() {
        if (!this.isPlaying) return;

        const currentElement = this.container.querySelector('.current-media');
        const nextElement = this.container.querySelector('.next-media');

        this.displayMedia(this.mediaItems[this.currentIndex], currentElement);
        
        const nextIndex = (this.currentIndex + 1) % this.mediaItems.length;
        this.displayMedia(this.mediaItems[nextIndex], nextElement);

        currentElement.style.display = 'flex';
        nextElement.style.display = 'none';

        setTimeout(() => {
            currentElement.style.display = 'none';
            nextElement.style.display = 'flex';
            console.log('Transitioning to next media:', nextIndex);

            this.currentIndex = nextIndex;
            if (this.isPlaying) this.startAnimation();
        }, this.transitionDuration);
    }

    displayMedia(mediaItem, element) {
        if (!mediaItem) {
            console.error('Media item is undefined');
            return;
        }
        
        const url = mediaItem.local_url || mediaItem.web_url;
        if (mediaItem.type === 'video') {
            element.innerHTML = `
                <video autoplay loop muted playsinline>
                    <source src="${url}" type="video/mp4">
                </video>`;
            console.log('Loading video:', url);
        } else {
            element.innerHTML = `<img src="${url}" alt="Media item">`;
            console.log('Loading image:', url);
        }
    }
}