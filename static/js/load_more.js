// static/js/load_more.js

document.addEventListener('DOMContentLoaded', function() {
    const loadMoreButton = document.getElementById('load-more');

    if (loadMoreButton) {
        loadMoreButton.addEventListener('click', function() {
            const nextPage = loadMoreButton.getAttribute('data-next-page');
            fetch(`/load-more-posts/?page=${nextPage}`)
                .then(response => response.text())
                .then(data => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(data, 'text/html');
                    const newPosts = doc.querySelectorAll('#post-list .preview, #post-list .detail');
                    const postList = document.getElementById('post-list');
                    newPosts.forEach(post => postList.appendChild(post));

                    const newNextPage = doc.querySelector('#load-more')?.getAttribute('data-next-page');
                    if (newNextPage) {
                        loadMoreButton.setAttribute('data-next-page', newNextPage);
                    } else {
                        loadMoreButton.remove();
                    }
                })
                .catch(error => console.error('Error loading more posts:', error));
        });
    }
});
