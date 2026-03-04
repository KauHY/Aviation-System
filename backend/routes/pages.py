from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

import app_state
from templates import templates

router = APIRouter()

@router.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/favicon.ico")
async def favicon():
    return RedirectResponse(url="/static/logo.svg")

@router.get("/login")
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/video-system")
async def video_system_page(request: Request):
    """远程视频协助系统页面"""
    return templates.TemplateResponse("video-system.html", {"request": request})

@router.get("/device-test")
async def device_test(request: Request):
    """设备测试页面"""
    return templates.TemplateResponse("device-test.html", {"request": request})

@router.get("/inspector-assignment")
async def inspector_assignment_page(request: Request):
    """检测人员分配管理页面"""
    return templates.TemplateResponse("inspector-assignment.html", {"request": request})

@router.get("/flight-search")
async def flight_search_page(request: Request):
    """航班查询页面"""
    airports = app_state.load_airport_data()
    return templates.TemplateResponse("flight-search.html", {"request": request, "airports": airports})

@router.get("/aircraft-info")
async def aircraft_info_page(request: Request):
    """航空器信息页面"""
    return templates.TemplateResponse("aircraft-info.html", {"request": request})

@router.get("/image-inspection")
async def image_inspection_page(request: Request):
    """图片检修页面"""
    return templates.TemplateResponse("image-inspection.html", {"request": request})

@router.get("/blockchain-deposit")
async def blockchain_deposit_page(request: Request):
    """区块链存证系统页面"""
    return templates.TemplateResponse("blockchain-deposit.html", {"request": request})

@router.get("/blockchain-deposit/records")
async def blockchain_records_page(request: Request):
    """维修记录列表页面"""
    return templates.TemplateResponse("blockchain-deposit-records.html", {"request": request})

@router.get("/blockchain-deposit/records/create")
async def blockchain_records_create_page(request: Request):
    """创建维修记录页面"""
    return templates.TemplateResponse("blockchain-deposit-records-create.html", {"request": request})

@router.get("/blockchain-deposit/audit")
async def blockchain_audit_page(request: Request):
    """审计日志页面"""
    return templates.TemplateResponse("blockchain-deposit.html", {"request": request})

@router.get("/blockchain-deposit/records/view/{record_id}")
async def blockchain_records_view_page(request: Request, record_id: str):
    """查看维修记录页面"""
    return templates.TemplateResponse("blockchain-deposit-records-view.html", {"request": request, "record_id": record_id})

@router.get("/blockchain-deposit/records/approve/{record_id}")
async def blockchain_records_approve_page(request: Request, record_id: str):
    """审批维修记录页面"""
    return templates.TemplateResponse("blockchain-deposit-records-approve.html", {"request": request, "record_id": record_id})

@router.get("/profile")
async def profile_page(request: Request):
    """个人管理页面"""
    return templates.TemplateResponse("profile.html", {"request": request})

@router.get("/system-settings")
async def system_settings_page(request: Request):
    """系统设置页面"""
    return templates.TemplateResponse("system-settings.html", {"request": request})

@router.get("/system-monitor")
async def system_monitor_page(request: Request):
    """系统监控页面"""
    return templates.TemplateResponse("system-monitor.html", {"request": request})

@router.get("/report-generation")
async def report_generation_page(request: Request):
    """报表生成页面"""
    return templates.TemplateResponse("report-generation.html", {"request": request})

@router.get("/permission-management")
async def permission_management_page(request: Request):
    """权限管理页面"""
    return templates.TemplateResponse("permission-management.html", {"request": request})

@router.get("/blockchain-visualization")
async def blockchain_visualization_page(request: Request):
    """区块链可视化页面"""
    return templates.TemplateResponse("blockchain-visualization.html", {"request": request})

@router.get("/inspection-management")
async def inspection_management_page(request: Request):
    """检修管理页面"""
    return templates.TemplateResponse("inspection-management.html", {"request": request})
