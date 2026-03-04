from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/api/image-inspection/analyze")
async def analyze_images(request: Request):
    """分析图片，调用teest中的模型"""
    try:
        from fastapi import UploadFile, File
        from ultralytics import YOLO
        from PIL import Image
        import numpy as np
        import os

        # 获取上传的文件
        form = await request.form()
        files = form.getlist("files")

        if not files:
            return {"success": False, "message": "请上传图片"}

        # 加载模型（强制使用CPU）
        model_path = os.path.join("..", "..", "teest", "model", "best.pt")
        model = YOLO(model_path)
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
