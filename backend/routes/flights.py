from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import app_state
from services.flight_workflow import FlightWorkflow

router = APIRouter()
flight_workflow = FlightWorkflow()

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
        new_id = flight_workflow.create_flight(app_state.flights, data)
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
        if not flight_workflow.update_flight(app_state.flights, flight_id, data):
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
