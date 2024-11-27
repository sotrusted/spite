// static/js/ajax_posts.js

const postForm = document.getElementById('post-form');

postForm.addEventListener('submit', function (e) {
    e.preventDefault(); // Prevent the default form submission

    refreshCSRFToken();

    const formData = new FormData(this); // Collect form data
    const url = this.action; // Get the form's action URL

    // Perform AJAX request
    fetch(url, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest', // Mark it as an AJAX request
            'X-CSRFToken': getCookie('csrftoken'), // Include CSRF token
        },
        body: formData,
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                postForm.reset(); // Clear the form
                enableSubmitButton();

                document.getElementById('post-success').style.display = 'block';
                document.getElementById('post-error').style.display = 'none';

                const post = data.post; 

                const newPost = addPostToPage(post);

                updateSpiteCounter();

                // Scroll slightly above the newly added post
                const newPostPosition = newPost.getBoundingClientRect().top + window.scrollY;
                const offset = 100; // Adjust this value for desired spacing
                window.scrollTo({
                    top: newPostPosition - offset,
                    behavior: 'smooth'
                });
            } else {
                // Display error message
                document.getElementById('post-error').style.display = 'block';
                document.getElementById('post-success').style.display = 'none';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('post-error').style.display = 'block';
            document.getElementById('post-success').style.display = 'none';
            enableSubmitButton();
        });
    });
