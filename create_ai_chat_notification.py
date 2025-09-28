#!/usr/bin/env python3
"""
Script to create the AI Chat notification for the home page.
Run this from the Django project root: python3 create_ai_chat_notification.py
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django
sys.path.append('/home/sargent/spite')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spite.settings')
django.setup()

from blog.models import SiteNotification
from django.utils.timezone import now

def create_ai_chat_notification():
    """Create the AI Chat notification for home page"""
    
    # Clear all existing notifications
    SiteNotification.objects.all().delete()
    
    # Create only the AI Chat notification
    notification = SiteNotification.objects.create(
        message='AI Chat - Chat with Jayden',
        priority='feature',
        notification_type='modal',
        expires_at=now() + timedelta(days=30),  # Expires in 30 days
        is_active=True
    )
    
    print(f"Created AI Chat notification: {notification.message}")
    print("This notification will appear on the home page as a modal.")
    print("When dismissed, it will scroll to the AI chat component.")

if __name__ == '__main__':
    create_ai_chat_notification()
