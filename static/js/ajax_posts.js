// static/js/ajax_posts.js

import { getCookie } from './modules/load_document_functions.js';
import { addPostToPage, updateSpiteCounter, enableSubmitButton, disableSubmitButton } from './modules/utility_functions.js';



export function initAjaxPostForm() {
    const postForm = document.getElementById('post-form');

    if (!postForm) {
        console.log('Post form not found');
        return;
    }

    postForm.addEventListener('submit', function (e) {
        console.log('Form submission started'); // Debug log
        e.preventDefault(); // Prevent the default form submission
        disableSubmitButton(postForm);

        const formData = new FormData(this); // Collect form data
        const url = this.action; // Get the form's action URL
        console.log('Submitting to URL:', url); // Debug log

        // Perform AJAX request
        fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest', // Mark it as an AJAX request
                'X-CSRFToken': getCookie('csrftoken'), // Include CSRF token
            },
            body: formData,
        })
            .then(response => {
                console.log('Response status:', response.status); // Debug log
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Response data:', data); // Debug log
                if (data.success) {
                    postForm.reset(); // Clear the form
                    enableSubmitButton(postForm);

                    document.getElementById('post-success').style.display = 'block';
                    document.getElementById('post-error').style.display = 'none';

                    const post = data.post; 
                    console.log('Adding post to page:', post); // Debug log

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
                    console.log('Form submission failed:', data); // Debug log
                    // Display error message
                    document.getElementById('post-error').style.display = 'block';
                    document.getElementById('post-success').style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Error details:', error); // Debug log

                // Log more details about the error
                if (error.message) {
                    console.error('Error message:', error.message);
                }
                if (error.stack) {
                    console.error('Error stack:', error.stack);
                }

                document.getElementById('post-error').style.display = 'block';
                document.getElementById('post-success').style.display = 'none';
                enableSubmitButton();
            });
    });
}

// Add this debug function
function logFormData(formData) {
    console.log('Form data contents:');
    for (let pair of formData.entries()) {
        if (pair[1] instanceof File) {
            console.log(pair[0], 'File:', pair[1].name, 'Size:', pair[1].size, 'Type:', pair[1].type);
        } else {
            console.log(pair[0], pair[1]);
        }
    }
}