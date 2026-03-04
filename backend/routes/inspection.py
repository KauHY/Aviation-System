import os
from pathlib import Path

from fastapi import APIRouter, Request

router = APIRouter()

MODEL_PATH_ENV = "YOLO_MODEL_PATH"
DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "inspection" / "best.pt"

@router.post("/api/image-inspection/analyze")
async def analyze_images(request: Request):
    """分析图片，调用YOLO模型"""
    try:
        from ultralytics import YOLO
        from PIL import Image
        import numpy as np

        # 获取上传的文件
        form = await request.form()
        files = form.getlist("files")

        if not files:
            return {"success": False, "message": "请上传图片"}

        # 加载模型（强制使用CPU）
        configured_path = os.getenv(MODEL_PATH_ENV, str(DEFAULT_MODEL_PATH))
        model_path = Path(configured_path).expanduser()
        if not model_path.is_absolute():
            model_path = (Path.cwd() / model_path).resolve()

        if not model_path.exists():
            return {
                "success": False,
                "message": f"模型文件不存在: {model_path}（可通过环境变量 {MODEL_PATH_ENV} 指定）"
            }

        model = YOLO(str(model_path))
        model.to('cpu')

        results = []

        for file in files:
            # 读取图片
            image = Image.open(file.file)
            img_array = np.array(image)

            # 预测
            prediction = model(img_array)
            result = prediction[0]

            # 获取预测结果
            max_idx = result.probs.top1
            predicted_class = result.names[max_idx]
            confidence = result.probs.top1conf.item()

            # 转换为normal/bad格式
            status = "normal" if predicted_class == "normal" else "bad"

            results.append({
                "filename": file.filename,
                "status": status
            })

        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "message": str(e)}
