# Generated manually to populate share_ids

from django.db import migrations
import secrets

def populate_share_ids(apps, schema_editor):
    AIChatSession = apps.get_model('blog', 'AIChatSession')
    for session in AIChatSession.objects.filter(share_id__isnull=True):
        session.share_id = secrets.token_urlsafe(24)
        session.save()

def reverse_populate_share_ids(apps, schema_editor):
    # Nothing to reverse
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0046_remove_sharedchat_chat_session_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_share_ids, reverse_populate_share_ids),
    ]
