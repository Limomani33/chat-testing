import asyncio
import aiohttp
from aiohttp import web
import json
import socket
import os

# ======================
# SETTINGS
# ======================
HTTP_PORT = int(os.environ.get("PORT", 8000))  # Render sets PORT env
WS_PATH = "/ws"

# ======================
# LAN IP
# ======================
def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

LAN_IP = get_lan_ip()

# ======================
# STORAGE
# ======================
clients = set()
users = {}
messages = []

# ======================
# HTTP APP
# ======================
app = web.Application()
routes = web.RouteTableDef()

@routes.get('/')
async def index(request):
    return web.FileResponse('index.html')

# Serve other static files if needed
@routes.get('/{filename}')
async def static_files(request):
    filename = request.match_info['filename']
    if os.path.exists(filename):
        return web.FileResponse(filename)
    return web.Response(status=404, text="Not Found")

app.add_routes(routes)

# ======================
# WEBSOCKET
# ======================
async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    clients.add(ws)

    # Send history
    await ws.send_json({"type":"history","messages":messages})

    try:
        async for msg in ws:
            if msg.type != aiohttp.WSMsgType.TEXT:
                continue
            data = json.loads(msg.data)

            if data["type"] == "join":
                users[ws] = data.get("name","Anonymous")

            elif data["type"] in ("message","image","audio"):
                payload = {
                    "type": data["type"],
                    "name": users.get(ws,"Anonymous"),
                    "content": data["content"],
                    "voice": data.get("voice", False)
                }
                messages.append(payload)
                # Broadcast
                for client in clients:
                    await client.send_json(payload)

    finally:
        clients.remove(ws)
        users.pop(ws, None)

    return ws

app.router.add_get(WS_PATH, ws_handler)

# ======================
# MAIN
# ======================
async def main():
    print(f"\n🫧 Soapy Chat running!")
    print(f"\n👉 Open this link on other devices:\n")
    print(f"   http://{LAN_IP}:{HTTP_PORT}\n")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', HTTP_PORT)
    await site.start()
    # Run forever
    while True:
        await asyncio.sleep(3600)

asyncio.run(main())
