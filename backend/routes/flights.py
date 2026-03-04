from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import app_state
from services.flight_workflow import FlightWorkflow

router = APIRouter()
flight_workflow = FlightWorkflow()


@router.post('/api/flight/search')
async def api_search_flight(request: Request):
    """兼容旧版航班查询接口"""
    try:
        data = await request.json()
        flight_number = str(data.get('flight_number', '')).strip()
        departure_airport = str(data.get('departure_airport', '')).strip()
        arrival_airport = str(data.get('arrival_airport', '')).strip()
        flight_date = str(data.get('flight_date', '')).strip()

        filtered_flights = []
        for flight in app_state.flights:
            if flight_number and str(flight.get('flight_number', '')) != flight_number:
                continue
            if departure_airport and str(flight.get('departure_airport', '')) != departure_airport:
                continue
            if arrival_airport and str(flight.get('arrival_airport', '')) != arrival_airport:
                continue
            if flight_date and str(flight.get('flight_date', '')) != flight_date:
                continue
            filtered_flights.append(flight)

        return JSONResponse(status_code=200, content={
            'success': True,
            'flights': filtered_flights
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            'success': False,
            'message': '查询航班失败: ' + str(e)
        })

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


@router.get('/api/flights/{flight_id}')
async def api_get_flight(flight_id: str):
    try:
        flight = next((item for item in app_state.flights if str(item.get('id')) == str(flight_id)), None)
        if not flight:
            return JSONResponse(status_code=404, content={
                'success': False,
                'message': '航班不存在'
            })

        return JSONResponse(status_code=200, content={
            'success': True,
            'flight': flight
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


@router.delete('/api/flights/{flight_id}')
async def api_delete_flight(flight_id: str):
    try:
        flight_index = next(
            (index for index, flight in enumerate(app_state.flights) if str(flight.get('id')) == str(flight_id)),
            None
        )
        if flight_index is None:
            return JSONResponse(status_code=404, content={
                'success': False,
                'message': '航班不存在'
            })

        app_state.flights.pop(flight_index)
        app_state.save_flights()

        return JSONResponse(status_code=200, content={
            'success': True,
            'message': '航班删除成功'
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            'success': False,
            'message': str(e)
        })
