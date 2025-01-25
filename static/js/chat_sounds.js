export const chatSounds = {
    message: new Audio('/static/sounds/message.mp3'),
    join: new Audio('/static/sounds/join.mp3'),
    leave: new Audio('/static/sounds/leave.mp3'),
    send: new Audio('/static/sounds/send.mp3')
};

// Initialize all sounds with low volume
Object.values(chatSounds).forEach(sound => {
    sound.volume = 0.3;
});

export function playSound(soundName) {
    if (chatSounds[soundName]) {
        chatSounds[soundName].currentTime = 0; // Reset sound
        chatSounds[soundName].play().catch(e => console.log('Sound play prevented'));
    }
}
