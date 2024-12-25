document.addEventListener('DOMContentLoaded', function () {
    const body = document.querySelector('body');
    const spiteBar = document.querySelector('.spite-bar');
    let snowflakeCount = 100;
    let isSnowing = false;
    let snowflakes = [];

    function createSnowflakes() {
        for (let i = 0; i < snowflakeCount; i++) {
            let snowflake = document.createElement('div');
            snowflake.className = 'snowflake';
            snowflake.style.left = Math.random() * 100 + '%';
            snowflake.style.animationDelay = Math.random() * 10 + 's';
            snowflake.style.animationDuration = 5 + Math.random() * 5 + 's';
            snowflakes.push(snowflake);
            body.appendChild(snowflake);
        }
    }

    function removeSnowflakes() {
        snowflakes.forEach(snowflake => snowflake.remove());
        snowflakes = [];
    }

    // Toggle Snowfall
    function toggleSnowfall() {
        if (isSnowing) {
            removeSnowflakes();
        } else {
            createSnowflakes();
        }
        isSnowing = !isSnowing;
    }

    // Toggle snowfall on
    toggleSnowfall();

    // Add Toggle Button
    const toggleButton = document.createElement('button');
    toggleButton.innerText = 'Toggle Snow';
    toggleButton.className = 'toggle-snow-btn';
    toggleButton.onclick = toggleSnowfall;
    spiteBar.appendChild(toggleButton);
});
