import os, json
from aiohttp import web

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

clients = set()
users = {}
messages = []

async def index(request):
    return web.FileResponse(os.path.join(BASE_DIR, "index.html"))

async def websocket_handler(request):
    ws = web.WebSocketResponse(max_msg_size=30_000_000)
    await ws.prepare(request)

    clients.add(ws)

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

                elif data["type"] in ("message", "image", "audio"):
                    payload = {
                        "type": data["type"],
                        "name": users.get(ws, "Anonymous"),
                        "content": data["content"],
                        "voice": data.get("voice", False)
                    }

                    messages.append(payload)
                    for c in clients:
                        await c.send_json(payload)
    finally:
        clients.remove(ws)
        users.pop(ws, None)

    return ws

app = web.Application()
app.router.add_get("/", index)
app.router.add_get("/ws", websocket_handler)

port = int(os.environ.get("PORT", 10000))
web.run_app(app, host="0.0.0.0", port=port)
