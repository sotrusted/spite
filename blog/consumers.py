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
