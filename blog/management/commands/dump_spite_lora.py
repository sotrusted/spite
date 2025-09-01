import json
from blog.models import Comment, Post
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Dump Spite Lora dataset'

    def handle(self, *args, **kwargs):
        self.stdout.write('Dumping Spite Lora dataset (structured posts and comments)...')
        
        output = []

        for comment in Comment.objects.select_related('post').all():
            if not comment.content.strip():
                continue

            post = comment.post
            if not post:
                continue

            text = f"{post.title or ''}\n{post.content or ''}".strip()
            response = comment.content.strip()


            output.append({
                "text": f"{text}",
                "completion": f"{response}"
            })

        with open("spite_lora_dataset_structured.jsonl", "w") as f:
            for item in output:
                f.write(json.dumps(item) + "\n")

        self.stdout.write('Dumping Spite Lora dataset (unstructured posts)...')

        output = []

        for post in Post.objects.all():
            text = f"{post.title}\n\n{post.content}".strip()
            if text:
                output.append({"text": text})

        with open("spite_lora_dataset_unstructured.txt", "w") as f:
            for item in output:
                f.write(json.dumps(item) + "\n")
        self.stdout.write('Done!')
