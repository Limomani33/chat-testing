import os
import json
import asyncio
from aiohttp import web
import aiohttp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ======================
# STATE
# ======================
clients = set()
users = {}          # ws -> username
messages = []       # capped at 15

# ======================
# HTTP
# ======================
async def index(request):
    return web.FileResponse(os.path.join(BASE_DIR, "index.html"))

# ======================
# PHID CHECK (mock-safe)
# ======================
async def check_phid(request):
    data = await request.json()
    phid = data.get("phid", "")

    # VERY light validation (you can replace with real API later)
    if not phid or len(phid) < 6:
        return web.json_response({"ok": False})

    # fake username derived from PHID
    username = f"user_{phid[-4:]}"
    return web.json_response({
        "ok": True,
        "username": username
    })

# ======================
# WEBSOCKET
# ======================
async def websocket_handler(request):
    ws = web.WebSocketResponse(max_msg_size=10_000_000)
    await ws.prepare(request)
    clients.add(ws)

    # send capped history
    await ws.send_json({
        "type": "history",
        "messages": messages
    })

    try:
        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue

            data = json.loads(msg.data)

            if data["type"] == "join":
                users[ws] = data["name"]

            elif data["type"] == "message":
                content = data["content"]

                # hard limit
                if len(content) > 300:
                    await ws.send_json({
                        "type": "error",
                        "message": "Message exceeds 300 characters"
                    })
                    continue

                payload = {
                    "type": "message",
                    "name": users.get(ws, "Anonymous"),
                    "content": content
                }

                messages.append(payload)
                if len(messages) > 15:
                    messages.pop(0)

                for c in clients:
                    await c.send_json(payload)

    finally:
        clients.discard(ws)
        users.pop(ws, None)

    return ws

# ======================
# KEEP ALIVE
# ======================
async def keep_alive():
    await asyncio.sleep(10)
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        return

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await session.get(url, timeout=10)
            except:
                pass
            await asyncio.sleep(360)

# ======================
# APP
# ======================
app = web.Application()
app.router.add_get("/", index)
app.router.add_post("/check_phid", check_phid)
app.router.add_get("/ws", websocket_handler)

app.on_startup.append(lambda app: asyncio.create_task(keep_alive()))

port = int(os.environ.get("PORT", 8000))
web.run_app(app, host="0.0.0.0", port=port)
