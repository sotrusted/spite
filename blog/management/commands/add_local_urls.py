from django.core.management.base import BaseCommand
import json
from django.conf import settings
import os
import logging

logger = logging.getLogger('spite')

class Command(BaseCommand):
    help = 'Add local URLs to existing media features JSON'

    def handle(self, *args, **kwargs):
        features_path = os.path.join(settings.MEDIA_ROOT, 'features', 'media_features.json')
        
        # Read existing JSON
        with open(features_path, 'r') as f:
            features_data = json.load(f)
        
        logger.info(f"Processing {len(features_data)} items")
        
        # Add local URLs
        for item in features_data:
            # Convert https://spite.fr/media/... to /media/...
            if 'url' in item:  # Handle old format
                web_url = item['url']
                item['web_url'] = web_url
                item['local_url'] = web_url.replace('https://spite.fr', '')
                del item['url']  # Remove old url field
        
        # Save updated JSON
        with open(features_path, 'w') as f:
            json.dump(features_data, f)
        
        logger.info("Successfully updated media features JSON")
