#!/usr/bin/env python3
"""
Script to create test notifications for the Spite notification system.
Run this from the Django project root: python3 create_test_notifications.py
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

def create_test_notifications():
    """Create various test notifications"""
    
    # Clear existing test notifications
    SiteNotification.objects.filter(message__icontains='test').delete()
    
    notifications = [
        {
            'message': 'A New Sick Freak has entered the chat',
            'priority': 'chat',
            'notification_type': 'floating',
            'expires_at': now() + timedelta(minutes=30),
        },
        {
            'message': 'AI Chat - Chat with Jayden',
            'priority': 'feature',
            'notification_type': 'modal',
            'expires_at': now() + timedelta(hours=24),
        },
        {
            'message': 'Welcome to Spite Magazine - where anyone can write for spite!',
            'priority': 'normal',
            'notification_type': 'floating',
            'expires_at': now() + timedelta(hours=1),
        },
        {
            'message': 'New feature: AI Chat is now available! Ask questions about Spite posts.',
            'priority': 'high',
            'notification_type': 'floating',
            'expires_at': now() + timedelta(hours=2),
        },
    ]
    
    created_count = 0
    for notif_data in notifications:
        notification = SiteNotification.objects.create(**notif_data)
        print(f"Created {notification.priority} {notification.notification_type} notification: {notification.message[:50]}...")
        created_count += 1
    
    print(f"\nCreated {created_count} test notifications!")
    print("Visit /chat/ to see them in action.")

if __name__ == '__main__':
    create_test_notifications()
