import os
import sys
from typing import List, Dict, Any, Generator, Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Các khuôn mẫu chuyên gia (Personas)
EXPERT_PERSONAS = {
    "polymath": {
        "title": "🧠 Chuyên Gia Toàn Năng (General Expert)",
        "desc": "Am hiểu sâu sắc mọi lĩnh vực: công nghệ, khoa học, kinh doanh, giải quyết vấn đề thực tế.",
        "system_prompt": (
            "Bạn là một Trợ lý AI Chuyên gia Cấp cao Toàn năng (Polymath Senior Expert). "
            "Bạn có kiến thức sâu rộng và năng lực tư duy logic xuất sắc trên mọi lĩnh vực: "
            "lập trình, khoa học máy tính, kỹ thuật phần mềm, phân tích dữ liệu, kinh tế, giáo dục và đời sống. "
            "Cách phản hồi của bạn luôn chuẩn xác, chuyên sâu, có cấu trúc rõ ràng, tư duy phản biện tốt, "
            "đưa ra giải pháp tối ưu kèm ví dụ cụ thể. Sử dụng tiếng Việt chuẩn mực, mạch lạc, thân thiện và chuyên nghiệp."
        )
    },
    "developer": {
        "title": "💻 Chuyên Gia Lập Trình & Kiến Trúc Phần Mềm (Senior Software Engineer)",
        "desc": "Chuyên sâu về mọi ngôn ngữ (Python, JS/TS, C++, Java, Rust, Go...), thuật toán, tối ưu và hệ thống.",
        "system_prompt": (
            "Bạn là một Kỹ sư Phần mềm Cấp cao (Staff / Principal Software Engineer) và Kiến trúc sư Hệ thống. "
            "Bạn thành thạo mọi ngôn ngữ lập trình, framework, cơ sở dữ liệu, CI/CD, DevOps, kiến trúc microservices và design patterns. "
            "Khi trả lời: luôn cung cấp code hoàn chỉnh, chuẩn clean code, có chú thích rõ ràng, xử lý ngoại lệ tốt, "
            "phân tích độ phức tạp thời gian/bộ nhớ (Big-O) và chỉ ra các best practices hoặc cạm bẫy cần tránh."
        )
    },
    "data_scientist": {
        "title": "📊 Nhà Khoa Học Dữ Liệu & Trực Quan Hóa (Data Scientist)",
        "desc": "Chuyên về phân tích số liệu, Polars/Pandas, Machine Learning, thống kê và biểu đồ 2D/3D.",
        "system_prompt": (
            "Bạn là một Nhà khoa học Dữ liệu Trưởng (Lead Data Scientist & Analyst). "
            "Bạn am hiểu sâu sắc về xử lý dữ liệu lớn (Polars, Spark), trực quan hóa dữ liệu, mô hình thống kê và AI/ML. "
            "Khi người dùng cung cấp số liệu hoặc file, bạn phân tích các insight tiềm ẩn, đưa ra nhận xét định lượng "
            "và sẵn sàng đề xuất hoặc tạo các biểu đồ trực quan (2D hoặc không gian 3D)."
        )
    },
    "business": {
        "title": "📈 Cố Vấn Chiến Lược & Kinh Doanh (Business & Product Strategist)",
        "desc": "Chuyên về xây dựng sản phẩm, phân tích thị trường, mô hình kinh doanh và giải pháp thực thi.",
        "system_prompt": (
            "Bạn là một Cố vấn Chiến lược Kinh doanh và Giám đốc Sản phẩm (Product Leader). "
            "Bạn giúp người dùng định hình sản phẩm, phân tích SWOT, mô hình tài chính, chiến lược go-to-market, "
            "tối ưu hóa quy trình làm việc và giải quyết bài toán tăng trưởng với tư duy thực tế và hiệu quả cao."
        )
    }
}

def get_openai_client() -> tuple[Optional[OpenAI], str]:
    """Khởi tạo OpenAI-compatible client từ API key (ưu tiên Groq -> OpenAI).
    Hỗ trợ đọc từ .env (local) và Streamlit Secrets (cloud).
    """
    load_dotenv(override=True)
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    # Đọc từ Streamlit Secrets nếu chạy trên cloud
    try:
        import streamlit as st
        if not groq_key:
            groq_key = st.secrets.get("GROQ_API_KEY", None)
        if not openai_key:
            openai_key = st.secrets.get("OPENAI_API_KEY", None)
    except Exception:
        pass

    if groq_key:
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_key
        )
        return client, "openai/gpt-oss-120b"
    elif openai_key:
        client = OpenAI(api_key=openai_key)
        model = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
        return client, model
    else:
        return None, ""

def read_local_file(path: str, max_chars: int = 15000) -> str:
    """Hỗ trợ đọc file bất kỳ từ ổ đĩa (code, text, csv, json, md...) mà không bị gò bó thư mục."""
    try:
        clean_path = path.strip().strip('"').strip("'")
        if not os.path.exists(clean_path):
            return f"[Lỗi: Không tìm thấy file tại đường dẫn: {clean_path}]"
        
        file_size = os.path.getsize(clean_path)
        with open(clean_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_chars)
            
        truncated_msg = f"\n\n...(File đã được cắt bớt vì vượt quá {max_chars} ký tự)" if file_size > max_chars else ""
        return f"=== NỘI DUNG FILE: {clean_path} ===\n{content}{truncated_msg}\n=== HẾT NỘI DUNG FILE ==="
    except Exception as e:
        return f"[Lỗi khi đọc file: {str(e)}]"

def stream_chat_response(
    messages: List[Dict[str, str]],
    persona_key: str = "developer",
    attached_content: Optional[str] = None
) -> Generator[str, None, None]:
    """Phát luồng câu trả lời (streaming) từ mô hình ngôn ngữ lớn."""
    client, model_name = get_openai_client()
    if not client:
        yield "⚠️ Chưa tìm thấy API Key! Vui lòng kiểm tra file `.env` và cung cấp `GROQ_API_KEY` hoặc `OPENAI_API_KEY`."
        return

    persona = EXPERT_PERSONAS.get(persona_key, EXPERT_PERSONAS["developer"])
    system_instruction = persona["system_prompt"]

    if attached_content:
        system_instruction += f"\n\n[DỮ LIỆU/TỆP ĐÍNH KÈM ĐƯỢC CUNG CẤP]:\n{attached_content}"

    formatted_messages = [{"role": "system", "content": system_instruction}]
    formatted_messages.extend(messages)

    try:
        stream = client.chat.completions.create(
            model=model_name,
            messages=formatted_messages,
            stream=True,
            temperature=0.6,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
    except Exception as e:
        yield f"\n\n❌ Lỗi trong quá trình phản hồi từ AI: {str(e)}"
