// Function to save input and hide the modal
function saveInput() {
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

