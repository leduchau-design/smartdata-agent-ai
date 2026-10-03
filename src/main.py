import os
import sys
from dotenv import load_dotenv

# Đảm bảo console Windows luôn xuất UTF-8 cho tiếng Việt
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()
from src.agents import create_analysis_crew

app = FastAPI(title="SmartData Agent Backend")

class AnalysisRequest(BaseModel):
    file_path: str
    question: str

from typing import List, Optional
from src.chat_service import stream_chat_response, read_local_file
from src.image_service import generate_ai_art, execute_chart_code

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    persona: Optional[str] = "developer"
    attached_path: Optional[str] = None

class ImageGenRequest(BaseModel):
    prompt: str
    width: Optional[int] = 800
    height: Optional[int] = 800
    model: Optional[str] = "flux"

class ChartCodeRequest(BaseModel):
    python_code: str

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "SmartData & Multi-Domain AI Expert"}

@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    try:
        attached_content = None
        if payload.attached_path and os.path.exists(payload.attached_path):
            attached_content = read_local_file(payload.attached_path)
            
        msg_dicts = [{"role": m.role, "content": m.content} for m in payload.messages]
        # Gom các chunk trả lời
        response_chunks = list(stream_chat_response(
            messages=msg_dicts,
            persona_key=payload.persona or "developer",
            attached_content=attached_content
        ))
        full_text = "".join(response_chunks)
        return {"status": "success", "response": full_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze")
async def analyze_data(payload: AnalysisRequest):
    if not os.path.exists(payload.file_path):
        raise HTTPException(status_code=404, detail="Không tìm thấy file dữ liệu.")
    
    try:
        # Kích hoạt CrewAI Agent xử lý ngầm
        crew = create_analysis_crew(payload.file_path, payload.question)
        result = await crew.kickoff_async()
        return {"status": "success", "result": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-image")
async def generate_image_endpoint(payload: ImageGenRequest):
    """Tạo ảnh nghệ thuật AI từ văn bản mô tả (text-to-image) sử dụng Pollinations AI."""
    try:
        from src.image_service import generate_ai_art_advanced
        image_path = generate_ai_art_advanced(
            prompt=payload.prompt,
            width=payload.width or 800,
            height=payload.height or 800,
            model=payload.model or "flux"
        )
        if image_path and os.path.exists(image_path):
            return {
                "status": "success",
                "image_path": image_path,
                "message": f"Đã tạo ảnh thành công tại {image_path}"
            }
        else:
            raise HTTPException(status_code=500, detail="Không thể tạo ảnh. Vui lòng thử lại với prompt khác.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/run-chart-code")
async def run_chart_code_endpoint(payload: ChartCodeRequest):
    """Thực thi code Python matplotlib để vẽ biểu đồ số liệu tùy chỉnh."""
    try:
        chart_path = execute_chart_code(payload.python_code)
        if chart_path and os.path.exists(chart_path):
            return {"status": "success", "chart_path": chart_path}
        else:
            raise HTTPException(status_code=500, detail="Không thể thực thi code biểu đồ.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
