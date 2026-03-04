import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import app_state

router = APIRouter()

# 简单的航班 API：列表 / 创建 / 更新
@router.get('/api/flights')
async def api_get_flights(request: Request):
    try:
        return JSONResponse(status_code=200, content={
            'success': True,
            'flights': app_state.flights
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            'success': False,
            'message': str(e)
        })


@router.post('/api/flights')
async def api_create_flight(request: Request):
    """创建航班并持久化到 flights.json"""
    try:
        data = await request.json()
        # 生成唯一 id
        new_id = str(uuid.uuid4())
        data['id'] = new_id
        # 添加到内存并保存
        app_state.flights.append(data)
        app_state.save_flights()
        return JSONResponse(status_code=200, content={
            'success': True,
            'flight': {'id': new_id}
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            'success': False,
            'message': str(e)
        })


@router.put('/api/flights/{flight_id}')
async def api_update_flight(flight_id: str, request: Request):
    """更新已有航班（按 id 匹配）"""
    try:
        data = await request.json()
        updated = False
        for idx, flight in enumerate(app_state.flights):
            if str(flight.get('id')) == str(flight_id):
                # 保持 id 不被覆盖
                data['id'] = flight_id
                app_state.flights[idx] = data
                updated = True
                break
        if not updated:
            return JSONResponse(status_code=404, content={
                'success': False,
                'message': '航班未找到'
            })
        app_state.save_flights()
        return JSONResponse(status_code=200, content={
            'success': True,
            'flight': {'id': flight_id}
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            'success': False,
            'message': str(e)
        })
