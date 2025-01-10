from django.core.management.base import BaseCommand
from django.conf import settings
import os
import json
import numpy as np
import logging

logger = logging.getLogger('spite')

class Command(BaseCommand):
    help = 'Sort media features by visual similarity'

    def handle(self, *args, **kwargs):
        features_path = os.path.join(settings.MEDIA_ROOT, 'features', 'media_features.json')
        sorted_path = os.path.join(settings.MEDIA_ROOT, 'features', 'sorted_media_features.json')
        
        logger.info(f"Reading features from {features_path}")
        
        try:
            with open(features_path, 'r') as f:
                features_data = json.load(f)
            
            logger.info(f"Loaded {len(features_data)} items")
            
            # Sort features
            sorted_features = [features_data[0]]
            remaining = features_data[1:]
            
            while remaining:
                last_item = sorted_features[-1]
                nearest_index = 0
                min_distance = float('inf')
                
                for i, item in enumerate(remaining):
                    distance = np.sqrt(np.sum(
                        (np.array(item['features']) - np.array(last_item['features'])) ** 2
                    ))
                    
                    if distance < min_distance:
                        min_distance = distance
                        nearest_index = i
                
                sorted_features.append(remaining.pop(nearest_index))
                
            logger.info(f"Sorting complete. Writing to {sorted_path}")
            
            # Save sorted features
            with open(sorted_path, 'w') as f:
                json.dump(sorted_features, f)
                
            logger.info("Successfully created sorted media features file")
            
        except Exception as e:
            logger.error(f"Error sorting media features: {str(e)}")
            raise 