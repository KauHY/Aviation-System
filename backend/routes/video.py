import uuid
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Body

import app_state

router = APIRouter()


class CreateRoomRequest(BaseModel):
    invited_users: Optional[List[str]] = []
    max_participants: Optional[int] = 10


@router.post("/create-room")
async def create_room(request: CreateRoomRequest = Body(...)):
    """创建新房间"""
    room_id = str(uuid.uuid4())[:8]
    
    app_state.rooms[room_id] = {
        "created_at": "now",
        "participants": [],
        "invited_users": request.invited_users,
        "max_participants": request.max_participants
    }
    
    return {
        "room_id": room_id,
        "invited_users": request.invited_users,
        "max_participants": request.max_participants
    }


@router.get("/room-info/{room_id}")
async def get_room_info(room_id: str):
    """获取房间信息"""
    # 检查房间是否存在
    if room_id not in app_state.rooms:
        return {
            "room_id": room_id,
            "status": "not_found",
            "participants": [],
            "participant_count": 0
        }
    
    room_data = app_state.rooms[room_id]
    
    if room_id in app_state.manager.active_connections:
        participants = app_state.manager.get_room_users(room_id)
        return {
            "room_id": room_id,
            "status": "active",
            "participants": participants,
            "participant_count": len(participants),
            "invited_users": room_data.get("invited_users", []),
            "max_participants": room_data.get("max_participants", 10)
        }

    return {
        "room_id": room_id,
        "status": "inactive",
        "participants": [],
        "participant_count": 0,
        "invited_users": room_data.get("invited_users", []),
        "max_participants": room_data.get("max_participants", 10)
    }


@router.post("/verify-room-access")
async def verify_room_access(room_id: str = Body(...), username: str = Body(...)):
    """验证用户是否有权限访问房间"""
    # 检查房间是否存在
    if room_id not in app_state.rooms:
        return {
            "allowed": False,
            "reason": "房间不存在"
        }
    
    room_data = app_state.rooms[room_id]
    invited_users = room_data.get("invited_users", [])
    
    # 如果没有邀请列表，允许所有人加入
    if not invited_users:
        return {"allowed": True}
    
    # 检查用户是否在邀请列表中
    if username in invited_users:
        return {"allowed": True}
    
    return {
        "allowed": False,
        "reason": "您没有权限加入此房间，请联系房间创建者"
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
