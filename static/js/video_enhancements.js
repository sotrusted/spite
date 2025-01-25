document.addEventListener('DOMContentLoaded', function() {
    const videoContainers = document.querySelectorAll('.video-container');
    
    videoContainers.forEach(container => {
        const video = container.querySelector('video');
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach(entry => {
                    if (!entry.isIntersecting && !video.paused) {
                        container.classList.add('sticky');
                    } else {
                        container.classList.remove('sticky');
                    }
                });
            },
            { threshold: 0.5 }
        );
        
        observer.observe(container);
        
        // Double tap to fullscreen on mobile
        let lastTap = 0;
        container.addEventListener('touchend', function(e) {
            const currentTime = new Date().getTime();
            const tapLength = currentTime - lastTap;
            if (tapLength < 500 && tapLength > 0) {
                if (document.fullscreenElement) {
                    document.exitFullscreen();
                } else {
                    container.requestFullscreen();
                }
                e.preventDefault();
            }
            lastTap = currentTime;
        });
    });
}); 