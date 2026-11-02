import json
import os
import random
import string
from aiohttp import web

ROOMS = {}


def generate_room_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=5))


async def index(request):
    return web.FileResponse("./index.html")


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    current_room = None
    player_id = id(ws)

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                action = data.get("action")

                if action == "create_room":
                    current_room = generate_room_code()
                    ROOMS[current_room] = {ws: player_id}
                    await ws.send_str(
                        json.dumps(
                            {"type": "room_created", "code": current_room}
                        )
                    )

                elif action == "join_room":
                    code = data.get("code", "").upper().strip()
                    if code in ROOMS:
                        current_room = code
                        ROOMS[current_room][ws] = player_id
                        await ws.send_str(
                            json.dumps(
                                {"type": "room_joined", "code": current_room}
                            )
                        )
                    else:
                        await ws.send_str(
                            json.dumps(
                                {
                                    "type": "error",
                                    "message": "Room does not exist!",
                                }
                            )
                        )

                elif action in ["move", "shoot"] and current_room in ROOMS:
                    data["id"] = player_id
                    raw = json.dumps(data)
                    for client in ROOMS[current_room]:
                        if client != ws:
                            await client.send_str(raw)
    finally:
        if current_room and current_room in ROOMS and ws in ROOMS[current_room]:
            del ROOMS[current_room][ws]
            if not ROOMS[current_room]:
                del ROOMS[current_room]

    return ws


app = web.Application()
app.router.add_get("/", index)
app.router.add_get("/ws", websocket_handler)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)