import os
import json
from aiohttp import web

# ======================
# Absolute path to current folder
# ======================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ======================
# HTTP: serve index.html
# ======================
async def index(request):
    # Always serve index.html from the same folder as server.py
    return web.FileResponse(os.path.join(BASE_DIR, "index.html"))

# ======================
# WEBSOCKET
# ======================
clients = set()
users = {}
messages = []

async def websocket_handler(request):
    ws = web.WebSocketResponse(max_msg_size=10_000_000)
    await ws.prepare(request)
    clients.add(ws)

    # Send chat history
    await ws.send_json({
        "type": "history",
        "messages": messages
    })

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data["type"] == "join":
                    users[ws] = data["name"]
                elif data["type"] in ("message", "image"):
                    payload = {
                        "type": data["type"],
                        "name": users.get(ws, "Anonymous"),
                        "content": data["content"]
                    }
                    messages.append(payload)
                    for client in clients:
                        await client.send_json(payload)
    finally:
        clients.remove(ws)
        users.pop(ws, None)

    return ws

# ======================
# APP SETUP
# ======================
app = web.Application()
app.router.add_get("/", index)
app.router.add_get("/ws", websocket_handler)

# Render sets the port in $PORT
port = int(os.environ.get("PORT", 8000))
web.run_app(app, host="0.0.0.0", port=port)
