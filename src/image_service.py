import os
import re
import urllib.parse
import time
import requests
from typing import Optional

os.makedirs("data/charts", exist_ok=True)

# Các model AI tạo ảnh có sẵn trên Pollinations
AVAILABLE_MODELS = {
    "flux": "FLUX (Chất lượng cao, cân bằng tốt - Mặc định)",
    "flux-realism": "FLUX Realism (Thực tế, chân dung, ảnh chụp)",
    "flux-anime": "FLUX Anime (Phong cách anime/manga Nhật Bản)",
    "flux-3d": "FLUX 3D (Mô hình 3D, render vật thể)",
    "turbo": "Turbo (Cực nhanh, phù hợp bản thảo)",
}


def generate_ai_art_advanced(
    prompt: str,
    width: int = 800,
    height: int = 800,
    model: str = "flux",
    seed: Optional[int] = None,
    enhance: bool = True,
    nologo: bool = True,
) -> Optional[str]:
    """Tạo ảnh AI chất lượng cao từ văn bản prompt với nhiều tùy chọn model và kích thước.
    
    Args:
        prompt: Văn bản mô tả ảnh cần tạo (tiếng Anh hoặc tiếng Việt)
        width: Chiều rộng ảnh (px), mặc định 800
        height: Chiều cao ảnh (px), mặc định 800
        model: Tên model AI (flux, flux-realism, flux-anime, flux-3d, turbo)
        seed: Hạt giống ngẫu nhiên để tái tạo kết quả (None = ngẫu nhiên)
        enhance: Tự động nâng cao chất lượng prompt (True/False)
        nologo: Ẩn logo watermark (True/False)
    
    Returns:
        Đường dẫn file ảnh đã lưu, hoặc None nếu thất bại
    """
    try:
        clean_prompt = prompt.strip().strip('"').strip("'")
        encoded_prompt = urllib.parse.quote(clean_prompt)
        
        # Xây dựng URL với các tham số đầy đủ
        params = {
            "width": width,
            "height": height,
            "model": model,
            "enhance": "true" if enhance else "false",
            "nologo": "true" if nologo else "false",
        }
        if seed is not None:
            params["seed"] = seed
            
        param_str = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?{param_str}"
        
        timestamp = int(time.time() * 1000)
        output_filename = f"ai_art_{timestamp}.jpg"
        output_path = os.path.abspath(os.path.join("data", "charts", output_filename))
        latest_path = os.path.abspath(os.path.join("data", "charts", "latest_ai_image.jpg"))

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=60)
        if resp.status_code == 200 and len(resp.content) > 1000:
            with open(output_path, "wb") as f_out:
                f_out.write(resp.content)
            with open(latest_path, "wb") as f_latest:
                f_latest.write(resp.content)
            return output_path
        else:
            print(f"[ImageService] HTTP {resp.status_code}, content size: {len(resp.content)}")
            return None
    except Exception as e:
        print(f"Error in generate_ai_art_advanced: {e}")
        return None


def generate_ai_art(prompt: str) -> Optional[str]:
    """Sinh ảnh nghệ thuật / tranh minh họa bằng AI từ văn bản prompt và lưu về file."""
    return generate_ai_art_advanced(prompt=prompt)


def execute_chart_code(python_code: str) -> Optional[str]:
    """Thực thi mã Python Matplotlib để vẽ biểu đồ số liệu hoặc đồ thị toán học."""
    try:
        chart_path = os.path.abspath(os.path.join("data", "charts", "latest_chart.png"))
        
        # Tiền xử lý code nếu có markdown fences
        clean_code = python_code.strip()
        if clean_code.startswith("```python"):
            clean_code = clean_code[9:]
        elif clean_code.startswith("```"):
            clean_code = clean_code[3:]
        if clean_code.endswith("```"):
            clean_code = clean_code[:-3]
            
        local_scope = {}
        exec_code = f"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

{clean_code}

plt.savefig(r'{chart_path}', bbox_inches='tight', dpi=130)
plt.close('all')
"""
        exec(exec_code, {}, local_scope)
        if os.path.exists(chart_path):
            return chart_path
        return None
    except Exception as e:
        print(f"Error in execute_chart_code: {e}")
        return None
