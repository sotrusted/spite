from django.test import TestCase, Client
from django.urls import reverse
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from django.core.files.uploadedfile import SimpleUploadedFile
from .consumers import PostConsumer, CommentConsumer
from .models import Post, Comment, ChatMessage
from .routing import websocket_urlpatterns
import json

class SpiteBackendTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create test post
        self.post = Post.objects.create(
            title="Test Post",
            content="Test Content",
            display_name="Tester",
            anon_uuid="test123"
        )
        
    async def test_post_websocket(self):
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            "/ws/posts/"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        
        # Test sending message
        await communicator.send_json_to({
            "message": {
                "title": "New Post",
                "content": "Websocket Post"
            }
        })
        
        response = await communicator.receive_json_from()
        self.assertIn('message', response)
        
        await communicator.disconnect()

    def test_post_creation(self):
        post_data = {
            'title': 'New Post',
            'content': 'Post Content',
            'display_name': 'Anonymous',
        }
        response = self.client.post(reverse('post-create'), post_data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(Post.objects.filter(title='New Post').exists())

    def test_comment_creation(self):
        comment_data = {
            'content': 'Test Comment',
            'post': self.post.id,
            'display_name': 'Commenter'
        }
        response = self.client.post(
            reverse('add-comment', kwargs={'post_id': self.post.id}),
            comment_data
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Comment.objects.filter(content='Test Comment').exists())

    def test_media_upload(self):
        # Create a test image file
        image_content = b'GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        image_file = SimpleUploadedFile(
            "test.gif",
            image_content,
            content_type="image/gif"
        )
        
        post_data = {
            'title': 'Media Post',
            'content': 'Post with Media',
            'media_file': image_file
        }
        response = self.client.post(reverse('post-create'), post_data)
        self.assertEqual(response.status_code, 302)
        post = Post.objects.get(title='Media Post')
        self.assertTrue(post.media_file)

    def test_chat_message_storage(self):
        ChatMessage.objects.create(
            content="Test Message",
            sender_id="test_user",
            room="test_room"
        )
        self.assertTrue(
            ChatMessage.objects.filter(content="Test Message").exists()
        )

    def test_post_list_view(self):
        response = self.client.get(reverse('post-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/post_list.html')

    def test_post_detail_view(self):
        response = self.client.get(
            reverse('post-detail', kwargs={'pk': self.post.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/post_detail.html')

    async def test_comment_websocket(self):
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            "/ws/comments/"
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        
        await communicator.send_json_to({
            "message": {
                "content": "Test Comment",
                "post_id": self.post.id
            }
        })
        
        response = await communicator.receive_json_from()
        self.assertIn('message', response)
        
        await communicator.disconnect()

    def test_spite_counter(self):
        initial_count = Post.objects.count()
        post_data = {'title': 'Spite Post', 'content': 'Increasing Spite'}
        self.client.post(reverse('post-create'), post_data)
        new_count = Post.objects.count()
        self.assertEqual(new_count, initial_count + 1)
