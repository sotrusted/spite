import json
from channels.generic.websocket import AsyncWebsocketConsumer

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
    waiting_users = []
    active_chats = {}

    async def connect(self):
        self.user_id = str(uuid.uuid4())
        await self.accept()
        
        # Add user to waiting list if no one is waiting
        if not self.waiting_users:
            self.waiting_users.append(self.user_id)
            await self.send(json.dumps({
                'type': 'status',
                'message': 'Waiting for someone to join...'
            }))
        else:
            # Match with waiting user
            partner_id = self.waiting_users.pop(0)
            self.active_chats[self.user_id] = partner_id
            self.active_chats[partner_id] = self.user_id
            
            # Notify both users of match
            await self.channel_layer.group_add(self.user_id, self.channel_name)
            await self.channel_layer.group_add(partner_id, self.channel_name)
            
            await self.channel_layer.group_send(
                self.user_id,
                {
                    'type': 'chat.matched',
                    'message': 'Connected to a stranger!'
                }
            )

    async def disconnect(self, close_code):
        if self.user_id in self.waiting_users:
            self.waiting_users.remove(self.user_id)
        
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

    async def receive(self, text_data):
        data = json.loads(text_data)
        if self.user_id in self.active_chats:
            partner_id = self.active_chats[self.user_id]
            await self.channel_layer.group_send(
                partner_id,
                {
                    'type': 'chat.message',
                    'message': data['message']
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message']
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