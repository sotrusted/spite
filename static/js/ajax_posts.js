// static/js/ajax_posts.js

import { getCookie } from './modules/load_document_functions.js';
import { addPostToPage, updateSpiteCounter, enableSubmitButton, disableSubmitButton } from './modules/utility_functions.js';



export function initAjaxPostForm() {
    const postForm = document.getElementById('post-form');

    postForm.addEventListener('submit', function (e) {
        e.preventDefault(); // Prevent the default form submission
        disableSubmitButton(postForm);

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
                    enableSubmitButton(postForm);

                    document.getElementById('post-success').style.display = 'block';
                    document.getElementById('post-error').style.display = 'none';

                    const post = data.post; 

                    const newPost = addPostToPage(post);

                    // Only scroll if post was added successfully
                    if (newPost) {
                        updateSpiteCounter();

                        // Wait for the post to be fully rendered
                        setTimeout(() => {
                            const newPostPosition = newPost.getBoundingClientRect().top + window.scrollY;
                            const offset = 100;
                            window.scrollTo({
                                top: newPostPosition - offset,
                                behavior: 'smooth'
                            });
                        }, 100); // Small delay to ensure post is rendered
                    } else {
                        console.log('Post was not added to page');
                    }
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
}
