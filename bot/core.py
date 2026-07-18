import asyncio
import json
import websockets
from config import BOT_TOKEN
from interaction_handler import handle_interaction

async def heartbeat(ws, interval):
    while True:
        await asyncio.sleep(interval / 1000)
        try:
            await ws.send(json.dumps({"op": 1, "d": None}))
        except websockets.ConnectionClosed:
            break

async def listen_to_discord(command_registry):
    url = "wss://gateway.discord.gg/?v=10&encoding=json"
    while True:
        try:
            async with websockets.connect(url) as ws:
                hello_msg = await ws.recv()
                interval = json.loads(hello_msg)['d']['heartbeat_interval']
                asyncio.create_task(heartbeat(ws, interval))
                
                await ws.send(json.dumps({
                    "op": 2,
                    "d": {
                        "token": BOT_TOKEN, "intents": 0,
                        "properties": {"os": "linux", "browser": "k8s_bot", "device": "k8s_bot"}
                    }
                }))
                print("🟢 Connected to Discord (Listening for events).")
                
                async for message in ws:
                    event = json.loads(message)
                    if event.get('t') == 'INTERACTION_CREATE':
                        asyncio.create_task(handle_interaction(event, command_registry))
        except Exception as err:
            print(f"🔌 Reconnecting to Gateway in 5s... ({err})")
            await asyncio.sleep(5)