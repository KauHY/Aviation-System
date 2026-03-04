from datetime import datetime

from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse, Response

import app_state
from services.system_workflow import SystemWorkflow

router = APIRouter()
system_workflow = SystemWorkflow()

@router.post("/api/system/backup")
async def backup_system():
    """备份系统数据"""
    try:
        backup_dir = "backups"
        files = [
            (app_state.USER_DATA_FILE, "users.json"),
            ("flights.json", "flights.json"),
            ("maintenance_records.json", "maintenance_records.json"),
            ("blockchain.json", "blockchain.json"),
            ("contracts.json", "contracts.json"),
            ("tasks.json", "tasks.json")
        ]
        backup_file, error = system_workflow.create_backup(backup_dir, files)
        if error:
            return JSONResponse(status_code=500, content={"error": "备份失败: " + error})

        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "备份成功",
            "backup_file": backup_file
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "备份失败: " + str(e)})


@router.get("/api/system/backup/download")
async def download_backup():
    """下载最新的备份文件"""
    try:
        backup_dir = "backups"
        latest_backup = system_workflow.get_latest_backup(backup_dir)
        if not latest_backup:
            return JSONResponse(status_code=404, content={"error": "没有可用的备份文件"})

        return FileResponse(
            path=latest_backup,
            filename=os.path.basename(latest_backup),
            media_type='application/zip'
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "下载失败: " + str(e)})


@router.post("/api/system/restore")
async def restore_system(backup: UploadFile = File(...)):
    """恢复系统数据"""
    try:
        restore_files = {
            "users.json": app_state.USER_DATA_FILE,
            "flights.json": "flights.json",
            "maintenance_records.json": "maintenance_records.json",
            "blockchain.json": "blockchain.json",
            "contracts.json": "contracts.json",
            "tasks.json": "tasks.json"
        }
        error = system_workflow.restore_backup(backup.file, restore_files)
        if error:
            return JSONResponse(status_code=500, content={"error": "恢复失败: " + error})

        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "恢复成功"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "恢复失败: " + str(e)})


@router.post("/api/system/clear-cache")
async def clear_cache():
    """清理系统缓存"""
    try:
        temp_dirs = ["temp", "cache", "__pycache__"]
        cache_cleared = system_workflow.clear_cache(temp_dirs)

        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "缓存清理成功" if cache_cleared else "没有需要清理的缓存"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "清理缓存失败: " + str(e)})


@router.post("/api/system/clear-logs")
async def clear_logs():
    """清理系统日志"""
    try:
        logs_cleared = system_workflow.clear_logs(".")

        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "日志清理成功" if logs_cleared else "没有需要清理的日志"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "清理日志失败: " + str(e)})


@router.post("/api/reports/generate")
async def generate_report(request: Request):
    """生成报表"""
    try:
        data = await request.json()
        report_type = data.get('type', 'summary')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        format_type = data.get('format', 'excel')
        report_detail_type = data.get('report_type', 'detail')
        filters = data.get('filters', '')

        # 生成报表数据
        report_data = await app_state.generate_report_data(
            report_type, start_date, end_date, report_detail_type, filters
        )

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type}_report_{timestamp}.{format_type}"

        # 根据格式生成文件
        if format_type == 'json':
            return JSONResponse(status_code=200, content={
                "success": True,
                "message": "报表生成成功",
                "filename": filename,
                "data": report_data
            })
        else:
            # 对于其他格式，返回下载链接
            return JSONResponse(status_code=200, content={
                "success": True,
                "message": "报表生成成功",
                "filename": filename,
                "download_url": f"/api/reports/download/{report_type}/{timestamp}",
                "data": report_data
            })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "生成报表失败: " + str(e)})


@router.get("/api/reports/download/{report_type}/{timestamp}")
async def download_report(report_type: str, timestamp: str):
    """下载报表"""
    try:
        # 根据报表类型和时间戳生成文件内容
        report_data = await app_state.generate_report_data(report_type, None, None, 'detail', '')

        # 生成CSV格式的内容
        csv_content = "报表类型,生成时间\n"
        csv_content += f"{report_type},{report_data['generated_at']}\n\n"
        csv_content += "数据详情:\n"

        for item in report_data.get('data', []):
            if isinstance(item, dict):
                csv_content += ",".join([str(v) for v in item.values()]) + "\n"

        # 添加UTF-8 BOM头（字节形式），确保中文正确显示
        csv_bytes = b'\xef\xbb\xbf' + csv_content.encode('utf-8')

        # 返回CSV文件
        return Response(
            content=csv_bytes,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={report_type}_report_{timestamp}.csv"
            }
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "下载报表失败: " + str(e)})


@router.get("/api/system/stats")
async def get_system_stats():
    """获取系统统计信息"""
    try:
        stats = {
            "total_users": len(app_state.users),
            "total_flights": len(app_state.flights),
            "total_records": len(app_state.maintenance_records),
            "total_blocks": len(app_state.contract_engine.get_all_blocks()) if app_state.contract_engine else 0,
            "total_contracts": len(app_state.contract_engine.contracts) if app_state.contract_engine else 0,
            "disk_usage": app_state.get_disk_usage(),
            "memory_usage": app_state.get_memory_usage(),
            "uptime": app_state.get_system_uptime()
        }

        return JSONResponse(status_code=200, content=stats)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取统计信息失败: " + str(e)})

@router.get("/api/system/users")
async def get_all_users_info(request: Request):
    """获取所有用户信息"""
    try:
        print(f"[DEBUG] 开始获取用户列表")
        print(f"[DEBUG] users变量: {app_state.users}")

        # 直接返回users数据
        users_list = []
        for username, user_info in app_state.users.items():
            users_list.append({
                "username": username,
                "role": user_info.get("role", "user") if isinstance(user_info, dict) else "user",
                "address": user_info.get("address", "") if isinstance(user_info, dict) else "",
                "email": user_info.get("email", "") if isinstance(user_info, dict) else "",
                "phone": user_info.get("phone", "") if isinstance(user_info, dict) else "",
                "specialty": user_info.get("specialty", "") if isinstance(user_info, dict) else "",
                "employee_id": user_info.get("employee_id", "") if isinstance(user_info, dict) else "",
                "created_at": user_info.get("created_at", "") if isinstance(user_info, dict) else ""
            })

        print(f"[DEBUG] 用户列表: {users_list}")

        return JSONResponse(status_code=200, content={
            "success": True,
            "users": users_list,
            "total": len(users_list)
        })
    except Exception as e:
        print(f"[ERROR] 获取用户信息失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": "获取用户信息失败: " + str(e)
        })
