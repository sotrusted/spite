export function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

export function logToBackend(message, level = 'info') {
    // Always log to console first
    console.log(`[${level}] ${message}`);
    
    // Then try to log to backend
    const baseUrl = window.location.origin;
    const csrfToken = getCookie('csrftoken');
    
    if (!csrfToken) {
        console.warn('CSRF token not found, skipping backend logging');
        return;
    }
    
    fetch(`/api/log-js/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken
        },
        body: `message=${encodeURIComponent(message)}&level=${level}`,
        credentials: 'same-origin'  // Include cookies
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .catch(error => {
        console.warn('Backend logging failed:', error);
        // Already logged to console above, so no need to duplicate
    });
}

// Helper function to set a cookie
export function setCookie(name, value, days) {
    const expires = new Date();
    expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
    document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/`;
}


export function scrollToElementById(id) {
    const targetElement = document.getElementById(id);
    const targetPosition = targetElement.getBoundingClientRect().top + window.scrollY;
    const offset = 100; // Adjust this value for desired spacing
    console.log(targetPosition - offset)
    window.scrollTo({
        top: targetPosition - offset,
    });
}

// Function to save input and hide the modal
export function saveInput() {
    // Select all input elements with the class or ID "user-input"
    const inputs = document.querySelectorAll("#user-input, .user-input"); // Adjust selectors as needed

    let userInput = null;

    // Loop through inputs and find the one with a value
    inputs.forEach(input => {
        if (input.value.trim()) {
            userInput = input.value.trim(); // Get the value
        }
    });
    

    if (!userInput) {
        alert("Please enter something before proceeding.");
        return;
    }

    // Save input via the API
    fetch('/api/save-list/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ input: userInput }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log("Input saved:", data);
                setCookie("input_shown", "true", 365); // Prevent the modal from showing again
                document.getElementById("modal-overlay").style.display = "none";
                document.body.classList.remove("modal-active"); // Re-enable scrolling
                inputs.forEach(input => {
                    if (input.value.trim()) {
                        input.value = ''; // Clear only the input that was used
                    }
                })
            } else {
                console.error("Error saving input:", data.error);
            }
        })
        .catch(error => console.error("API Error:", error));
}



// Function to show the modal if the cookie is not set
export function showModalIfNeeded() {
    const alreadyShown = getCookie("input_shown");
    console.log("Input shown: " + alreadyShown);
    const modalOverlay = document.getElementById("modal-overlay");
    if (modalOverlay) {
        if (!alreadyShown) {
            modalOverlay.style.display = "flex";
            document.body.classList.add("modal-active"); // Disable scrolling
            // loadWordCloud(); // Load word cloud
        }
        else {
            modalOverlay.style.display = "none";
            document.body.classList.remove("modal-active");
        }
    } else {
        console.error("Modal overlay not found");
    }
}


// Function to refresh the csrf token in the DOM 
export async function refreshCSRFToken() {
    try {
        const response = await fetch('/get-csrf-token/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        // Create csrf input if it doesn't exist
        let csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (!csrfInput) {
            csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            document.body.appendChild(csrfInput);
        }
        csrfInput.value = data.csrfToken;
        
        // Also set as cookie for redundancy
        document.cookie = `csrftoken=${data.csrfToken};path=/`;
        
        return data.csrfToken;
    } catch (error) {
        console.error("Error refreshing CSRF token:", error);
        throw error;
    }
}


