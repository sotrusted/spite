import json
import uuid
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage
from django.utils import timezone
from .models import SecureIPStorage
from weakref import WeakSet
import asyncio
from spite.context_processors import get_optimized_posts

logger = logging.getLogger('spite')

class PostConsumer(AsyncWebsocketConsumer):
    # Track active connections
    active_connections = WeakSet()
    
    async def connect(self):
        """Simple connection handler for live updates"""
        self.active_connections.add(self)
        await self.channel_layer.group_add("posts", self.channel_name)
        await self.accept()
        
        # Set ping interval for connection health
        self.ping_task = asyncio.create_task(self.ping_client())
    
    async def disconnect(self, close_code):
        """Clean disconnect"""
        self.active_connections.discard(self)
        await self.channel_layer.group_discard("posts", self.channel_name)
        self.ping_task.cancel()
    
    async def receive(self, text_data):
        """Handle incoming post data"""
        try:
            data = json.loads(text_data)
            # Broadcast new post to all connected clients

            if data.get("type") == "ping" or data.get("type") == "pong":
                return
        
            if "message" not in data:
                logger.error(f"No message in data: {data}")
                return

            await self.channel_layer.group_send(
                "posts",
                {
                    "type": "post_message",
                    "message": data["message"]
                }
            )
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {data}")
        except Exception as e:
            logger.error(f"Error in post consumer receive: {str(e)}", exc_info=True)
    
    async def post_message(self, event):
        """Send new post to client"""
        try:
            await self.send(text_data=json.dumps({
                "message": event["message"]
            }))
        except Exception as e:
            logger.error(f"Error sending post message: {e}")
    
    async def ping_client(self):
        """Keep connection alive"""
        while True:
            try:
                await asyncio.sleep(30)
                await self.send(text_data=json.dumps({"type": "ping"}))
            except Exception:
                break


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
    # Class variables to store waiting users, active chat pairs, and online users
    waiting_users = []  # Class variable to store waiting users
    active_chats = {}   # Class variable to store active chat pairs
    online_users = set()  # Class variable to track all online users


    storage = SecureIPStorage()

    def get_client_ip(self):
        # Convert headers list of tuples to a dict for easier lookup
        headers = dict(self.scope['headers'])
        
        # Get X-Forwarded-For header, converting from bytes to string if it exists
        forwarded_for = headers.get(b'x-forwarded-for', b'').decode()
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        # If no X-Forwarded-For header, get client address from scope
        return self.scope['client'][0] if self.scope.get('client') else None

    async def connect(self):
        self.user_id = str(uuid.uuid4())
        client_ip = self.get_client_ip()
        self.client_ip = self.storage.decrypt_ip(client_ip)
        logger.info(f"New chat connection: {self.user_id}")
        
        # Add user to online users set
        self.__class__.online_users.add(self.user_id)
        logger.info(f"Added user to online_users. Current users: {self.__class__.online_users}")
        
        # Accept the connection first
        await self.accept()
        logger.info(f"WebSocket connection accepted for user {self.user_id}")

        # Send initial user count to this client
        await self.send(text_data=json.dumps({
            'type': 'user_count',
            'count': len(self.__class__.online_users)
        }))
        logger.info(f"Sent initial user count to client: {len(self.__class__.online_users)}")
        
        # Then add to groups and broadcast to others
        await self.channel_layer.group_add(self.user_id, self.channel_name)
        await self.channel_layer.group_add("chat_updates", self.channel_name)
        logger.info(f"Added user {self.user_id} to groups")

        # Broadcast updated count to all other clients
        await self.channel_layer.group_send(
            "chat_updates",
            {
                "type": "chat.user_count",
                "count": len(self.__class__.online_users)
            }
        )
        
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
        
        # Remove from online users set first
        self.__class__.online_users.discard(self.user_id)
        logger.info(f"Removed user from online_users. Current users: {self.__class__.online_users}")
        
        # Handle rest of disconnect logic
        if self.user_id in self.waiting_users:
            self.waiting_users.remove(self.user_id)
            logger.info(f"Removed {self.user_id} from waiting list")
        
        if self.user_id in self.active_chats:
            partner_id = self.active_chats[self.user_id]
            await self.channel_layer.group_send(
                partner_id,
                {
                    'type': 'chat.disconnected',
                    'message': 'Stranger has disconnected'
                }
            )
            
            del self.active_chats[self.user_id]
            del self.active_chats[partner_id]
            logger.info(f"Ended chat between {self.user_id} and {partner_id}")
        
        # Remove from channel groups
        await self.channel_layer.group_discard(self.user_id, self.channel_name)
        await self.channel_layer.group_discard("chat_updates", self.channel_name)

        # Broadcast updated user count after disconnect
        await self.broadcast_user_count()

    async def broadcast_user_count(self):
        """Helper method to broadcast current user count to all clients"""
        try:
            count = len(self.__class__.online_users)
            logger.info(f"Broadcasting user count: {count} (Users: {self.__class__.online_users})")
            
            # First try sending directly to the current client
            try:
                await self.send(text_data=json.dumps({
                    'type': 'user_count',
                    'count': count
                }))
                logger.info(f"Sent user count directly to client: {self.channel_name}")
            except Exception as e:
                logger.error(f"Error sending direct user count to client: {str(e)}")
            
            # Then try broadcasting to all clients
            try:
                await self.channel_layer.group_send(
                    "chat_updates",
                    {
                        "type": "chat.user_count",
                        "count": count
                    }
                )
                logger.info(f"Successfully broadcast user count to chat_updates group")
            except Exception as e:
                logger.error(f"Error broadcasting to chat_updates group: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error in broadcast_user_count: {str(e)}")

    async def chat_user_count(self, event):  # Rename to match the type
        """Send user count update to WebSocket"""
        logger.info(f"Sending user count update to client: {event['count']}")
        try:
            await self.send(text_data=json.dumps({
                'type': 'user_count',  # Keep the client-side type the same
                'count': event['count']
            }))
            logger.info(f"Successfully sent user count to client")
        except Exception as e:
            logger.error(f"Error sending user count to client: {str(e)}")

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
            ip_address=self.client_ip
        )
        return msg.timestamp.isoformat()