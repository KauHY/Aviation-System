import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import app_state

router = APIRouter()


@router.post("/create-room")
async def create_room():
    """创建新房间"""
    room_id = str(uuid.uuid4())[:8]
    app_state.rooms[room_id] = {
        "created_at": "now",
        "participants": []
    }
    return {"room_id": room_id}


@router.get("/room-info/{room_id}")
async def get_room_info(room_id: str):
    """获取房间信息"""
    if room_id in app_state.manager.active_connections:
        participants = app_state.manager.get_room_users(room_id)
        return {
            "room_id": room_id,
            "status": "active",
            "participants": participants,
            "participant_count": len(participants)
        }

    return {
        "room_id": room_id,
        "status": "inactive",
        "participants": [],
        "participant_count": 0
    }


@router.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    await app_state.manager.connect(websocket, room_id, user_id)

    await app_state.manager.broadcast({
        "type": "user_joined",
        "user_id": user_id
    }, room_id)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "chat_message":
                await app_state.manager.broadcast({
                    "type": "chat_message",
                    "user_id": user_id,
                    "message": data.get("message"),
                    "timestamp": data.get("timestamp")
                }, room_id)
            elif "target_id" in data:
                target_id = data["target_id"]
                if room_id in app_state.manager.active_connections:
                    if target_id in app_state.manager.active_connections[room_id]:
                        await app_state.manager.active_connections[room_id][target_id].send_json(data)
            else:
                await app_state.manager.broadcast(data, room_id, user_id)
    except WebSocketDisconnect:
        app_state.manager.disconnect(room_id, user_id)
        await app_state.manager.broadcast({
            "type": "user_left",
            "user_id": user_id
        }, room_id)
