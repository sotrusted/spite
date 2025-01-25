import json
import uuid
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage
from django.utils import timezone

logger = logging.getLogger('spite')

class PostConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Add the user to a group for broadcasting
        await self.channel_layer.group_add("posts", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Remove the user from the group
        await self.channel_layer.group_discard("posts", self.channel_name)

    async def receive(self, text_data):
        # Handle incoming data from WebSocket (if needed)
        data = json.loads(text_data)
        await self.channel_layer.group_send(
            "posts",
            {
                "type": "post_message",
                "message": data["message"],
            },
        )

    async def post_message(self, event):
        # Send the message to WebSocket
        await self.send(text_data=json.dumps({
            "message": event["message"]
        }))


class CommentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Subscribe to the "comments" group
        await self.channel_layer.group_add("comments", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Unsubscribe from the "comments" group
        await self.channel_layer.group_discard("comments", self.channel_name)

    async def comment_message(self, event):
        # Send the comment message to the WebSocket
        await self.send(text_data=json.dumps(event["message"]))


class ChatConsumer(AsyncWebsocketConsumer):
    waiting_users = []  # Class variable to store waiting users
    active_chats = {}   # Class variable to store active chat pairs

    async def connect(self):
        self.user_id = str(uuid.uuid4())
        logger.info(f"New chat connection: {self.user_id}")
        
        # Add the user to their personal channel group
        await self.channel_layer.group_add(self.user_id, self.channel_name)
        await self.accept()
        
        if not self.waiting_users:
            # First user waiting
            self.waiting_users.append(self.user_id)
            await self.save_chat_message(
                message='Waiting for someone to join...',
                sender_id=self.user_id,
                chat_session=self.user_id,
                message_type='status'
            )
            await self.send(json.dumps({
                'type': 'status',
                'message': 'Waiting for someone to join...'
            }))
        else:
            # Match with waiting user
            partner_id = self.waiting_users.pop(0)
            chat_session = f"{min(self.user_id, partner_id)}-{max(self.user_id, partner_id)}"
            
            # Update active_chats for both users
            self.active_chats[self.user_id] = partner_id
            self.active_chats[partner_id] = self.user_id
            
            # Notify both users
            await self.channel_layer.group_send(
                partner_id,
                {
                    'type': 'chat.matched',
                    'message': 'Connected to a stranger!'
                }
            )
            
            await self.channel_layer.group_send(
                self.user_id,
                {
                    'type': 'chat.matched',
                    'message': 'Connected to a stranger!'
                }
            )
            
            await self.save_chat_message(
                message='Connected to a stranger!',
                sender_id=self.user_id,
                chat_session=chat_session,
                message_type='matched'
            )

    async def disconnect(self, close_code):
        logger.info(f"Chat disconnection: {self.user_id}")
        
        # Remove from waiting list if present
        if self.user_id in self.waiting_users:
            self.waiting_users.remove(self.user_id)
            logger.info(f"Removed {self.user_id} from waiting list")
        
        # Handle active chat disconnection
        if self.user_id in self.active_chats:
            partner_id = self.active_chats[self.user_id]
            await self.channel_layer.group_send(
                partner_id,
                {
                    'type': 'chat.disconnected',
                    'message': 'Stranger has disconnected'
                }
            )
            
            # Clean up active_chats
            del self.active_chats[self.user_id]
            del self.active_chats[partner_id]
            logger.info(f"Ended chat between {self.user_id} and {partner_id}")
        
        # Remove from channel group
        await self.channel_layer.group_discard(self.user_id, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        logger.info(f"Chat message from {self.user_id}: {data}")
        
        if self.user_id in self.active_chats:
            partner_id = self.active_chats[self.user_id]
            chat_session = f"{min(self.user_id, partner_id)}-{max(self.user_id, partner_id)}"
            
            # Save message and get timestamp
            timestamp = await self.save_chat_message(
                message=data['message'],
                sender_id=self.user_id,
                chat_session=chat_session,
                message_type='message'
            )
            
            await self.channel_layer.group_send(
                partner_id,
                {
                    'type': 'chat.message',
                    'message': data['message'],
                    'timestamp': timestamp
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'timestamp': event.get('timestamp', timezone.now().isoformat())
        }))

    async def chat_matched(self, event):
        await self.send(text_data=json.dumps({
            'type': 'matched',
            'message': event['message']
        }))

    async def chat_disconnected(self, event):
        await self.send(text_data=json.dumps({
            'type': 'disconnected',
            'message': event['message']
        }))

    @database_sync_to_async
    def save_chat_message(self, message, sender_id, chat_session, message_type):
        msg = ChatMessage.objects.create(
            message=message,
            sender_id=sender_id,
            chat_session=chat_session,
            message_type=message_type,
            ip_address=self.scope.get('client')[0] if self.scope.get('client') else None
        )
        return msg.timestamp.isoformat()