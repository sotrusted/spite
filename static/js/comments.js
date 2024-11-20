// static/js/comments.js 

document.addEventListener('DOMContentLoaded', function() {
        // Add click listeners for each toggle button
        document.querySelectorAll('.toggle-comments').forEach(button => {
            button.addEventListener('click', function() {
                const postId = this.dataset.postId;
                const commentsContainer = document.getElementById(`comments-container-${postId}`);
                
                // Toggle visibility of the comments container
                commentsContainer.style.display = commentsContainer.style.display === 'none' ? 'block' : 'none';
            });
        });
    });
