function toggleContent(postId) {
    var detailDiv = document.getElementById('post-detail-' + postId);
    var previewDiv = document.getElementById('post-preview-' + postId);
    if (detailDiv.style.display === 'none' && previewDiv.style.display === 'block') {
        detailDiv.style.display = 'block';
        previewDiv.style.display = 'none';
    } else {
        detailDiv.style.display = 'none';
        previewDiv.style.display = 'block';
    }
}