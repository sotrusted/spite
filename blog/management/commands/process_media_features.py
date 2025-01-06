from django.core.management.base import BaseCommand
from blog.models import Post
import cv2
import numpy as np
import json
from django.conf import settings
import os
import logging
from urllib.parse import unquote

logger = logging.getLogger('spite')

class Command(BaseCommand):
    help = 'Process all media files and store their OpenCV features'

    def handle(self, *args, **kwargs):
        features_dir = os.path.join(settings.MEDIA_ROOT, 'features')
        os.makedirs(features_dir, exist_ok=True)
        
        features_data = []
        posts = Post.objects.filter(media_file__isnull=False) | Post.objects.filter(image__isnull=False)
        total_posts = posts.count()
        
        logger.info(f"Starting media processing for {total_posts} posts with media")
        
        for index, post in enumerate(posts, 1):
            try:
                # Debug path resolution
                if getattr(post, 'media_file', None):
                    file_field = post.media_file
                    media_url = post.media_file.url
                elif getattr(post, 'image', None):
                    file_field = post.image
                    media_url = post.image.url
                else:
                    continue

                # Try different path resolutions
                media_path = file_field.path  # Django's path
                abs_path = os.path.join(settings.MEDIA_ROOT, file_field.name)  # Constructed path
                url_path = unquote(file_field.url)  # URL decoded path
                
                logger.info(f"Processing {index}/{total_posts}: Post {post.id}")
                logger.info(f"Django path: {media_path}")
                logger.info(f"Absolute path: {abs_path}")
                logger.info(f"URL path: {url_path}")

                # Try reading with different paths
                img = None
                paths_to_try = [media_path, abs_path, os.path.join(settings.BASE_DIR, url_path.lstrip('/'))]
                
                for path in paths_to_try:
                    logger.info(f"Trying to read: {path}")
                    img = cv2.imread(path)
                    if img is not None:
                        logger.info(f"Successfully read image from: {path}")
                        break

                if img is None:
                    logger.warning(f"Could not read media file for post {post.id} from any path")
                    continue

                # Convert to grayscale
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # Use SIFT for feature detection
                sift = cv2.SIFT_create()
                keypoints, descriptors = sift.detectAndCompute(gray, None)
                
                if descriptors is not None:
                    # Calculate average descriptor
                    avg_descriptor = np.mean(descriptors, axis=0).tolist()
                    
                    # Store features
                    features_data.append({
                        'id': post.id,
                        'url': media_url,
                        'type': 'video' if getattr(post, 'is_video', lambda: False)() else 'image',
                        'features': avg_descriptor
                    })
                    
                    logger.info(f"Successfully processed post {post.id}")
                else:
                    logger.warning(f"No features detected for post {post.id}")
                
            except Exception as e:
                logger.error(f"Error processing post {post.id}: {str(e)}", exc_info=True)
                continue

            # Save progress periodically
            if index % 10 == 0:
                features_path = os.path.join(features_dir, 'media_features.json')
                with open(features_path, 'w') as f:
                    json.dump(features_data, f)
                logger.info(f"Progress saved: {index}/{total_posts} items processed")

        # Final save
        features_path = os.path.join(features_dir, 'media_features.json')
        with open(features_path, 'w') as f:
            json.dump(features_data, f)
        
        logger.info(f'Successfully processed {len(features_data)} media items')