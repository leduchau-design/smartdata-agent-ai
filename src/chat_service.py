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

# Danh sách đuôi file được hỗ trợ đọc nội dung khi quét thư mục hoặc giải nén zip
SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".scss", ".json",
    ".csv", ".txt", ".md", ".sql", ".yaml", ".yml", ".env", ".sh", ".bat",
    ".ps1", ".java", ".cpp", ".c", ".h", ".hpp", ".cs", ".go", ".rs", ".php",
    ".rb", ".xml", ".toml", ".ini", ".cfg", ".proto", ".vue", ".svelte"
}

IGNORE_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "venv", ".venv", "env",
    "__pycache__", ".idea", ".vscode", "dist", "build", ".next",
    ".nuxt", "target", "bin", "obj", ".streamlit", ".gemini"
}

def select_folder_dialog() -> str:
    """Mở hộp thoại chọn thư mục của Windows (native folder picker)."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder_selected = filedialog.askdirectory()
        root.destroy()
        return folder_selected or ""
    except Exception:
        return ""

def read_local_directory(dir_path: str, max_files: int = 15, max_chars_per_file: int = 1500, max_total_chars: int = 6000) -> str:
    """Đọc cấu trúc và nội dung các file văn bản/code trong thư mục bất kỳ trên máy tính."""
    try:
        clean_path = dir_path.strip().strip('"').strip("'")
        if not os.path.exists(clean_path):
            return f"[Lỗi: Không tìm thấy thư mục tại: {clean_path}]"
        if not os.path.isdir(clean_path):
            return f"[Lỗi: Đường dẫn không phải là thư mục: {clean_path}]"

        tree_lines = []
        files_to_read = []

        for root, dirs, files in os.walk(clean_path):
            # Lọc bỏ thư mục không cần thiết
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
            rel_dir = os.path.relpath(root, clean_path)
            indent = "  " * (0 if rel_dir == "." else rel_dir.count(os.sep) + 1)
            
            if rel_dir != ".":
                tree_lines.append(f"{indent}📁 {os.path.basename(root)}/")
                
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                rel_f_path = os.path.normpath(os.path.join(rel_dir, f)) if rel_dir != "." else f
                tree_lines.append(f"{indent}  📄 {f}")
                if ext in SUPPORTED_EXTENSIONS and len(files_to_read) < max_files:
                    files_to_read.append((os.path.join(root, f), rel_f_path))

        tree_summary = "\n".join(tree_lines[:80])
        if len(tree_lines) > 80:
            tree_summary += f"\n  ...(và {len(tree_lines) - 80} mục khác)..."

        content_parts = [
            f"=== THƯ MỤC DỰ ÁN: {clean_path} ===",
            f"[CẤU TRÚC THƯ MỤC ({len(tree_lines)} mục)]:\n{tree_summary}\n",
            f"[NỘI DUNG CÁC TỆP ĐƯỢC NẠP ({len(files_to_read)} tệp)]:"
        ]

        total_chars = sum(len(p) for p in content_parts)
        read_count = 0

        for full_p, rel_p in files_to_read:
            if total_chars >= max_total_chars:
                content_parts.append(f"\n...(Đã đạt giới hạn dung lượng context {max_total_chars} ký tự, dừng nạp thêm tệp)...")
                break
            try:
                with open(full_p, "r", encoding="utf-8", errors="replace") as f_obj:
                    chunk = f_obj.read(max_chars_per_file)
                part = f"\n--- TỆP: {rel_p} ---\n{chunk}\n--- HẾT TỆP: {rel_p} ---"
                content_parts.append(part)
                total_chars += len(part)
                read_count += 1
            except Exception:
                continue

        content_parts.append(f"\n=== HẾT THƯ MỤC ({read_count}/{len(files_to_read)} tệp được nạp) ===")
        return "\n".join(content_parts)
    except Exception as e:
        return f"[Lỗi khi quét thư mục: {str(e)}]"

def read_zip_archive(zip_source, filename: str = "project.zip", max_files: int = 15, max_chars_per_file: int = 1500, max_total_chars: int = 6000) -> str:
    """Đọc tệp nén zip chứa folder dự án từ buffer hoặc đường dẫn file."""
    import zipfile
    import io
    try:
        if isinstance(zip_source, (bytes, bytearray)):
            zf = zipfile.ZipFile(io.BytesIO(zip_source))
        elif hasattr(zip_source, "read"):
            zf = zipfile.ZipFile(zip_source)
        elif isinstance(zip_source, str) and os.path.isfile(zip_source):
            zf = zipfile.ZipFile(zip_source)
        else:
            return "[Lỗi: Nguồn tệp zip không hợp lệ]"

        with zf:
            namelist = zf.namelist()
            valid_entries = []
            files_to_read = []
            for name in namelist:
                parts = name.split("/")
                if any(p in IGNORE_DIRS or p.startswith(".") for p in parts if p):
                    continue
                valid_entries.append(name)
                ext = os.path.splitext(name)[1].lower()
                if not name.endswith("/") and ext in SUPPORTED_EXTENSIONS:
                    if len(files_to_read) < max_files:
                        files_to_read.append(name)

            tree_summary = "\n".join([f"  📄 {n}" for n in valid_entries[:80]])
            if len(valid_entries) > 80:
                tree_summary += f"\n  ...(và {len(valid_entries) - 80} mục khác)..."

            content_parts = [
                f"=== TẬP TIN NÉN DỰ ÁN (.ZIP): {filename} ===",
                f"[CẤU TRÚC THƯ MỤC ({len(valid_entries)} mục)]:\n{tree_summary}\n",
                f"[NỘI DUNG CÁC TỆP ({len(files_to_read)} tệp)]:"
            ]

            total_chars = sum(len(p) for p in content_parts)
            read_count = 0
            for name in files_to_read:
                if total_chars >= max_total_chars:
                    content_parts.append(f"\n...(Đã đạt giới hạn dung lượng context {max_total_chars} ký tự, dừng nạp thêm tệp)...")
                    break
                try:
                    with zf.open(name) as f_obj:
                        data = f_obj.read(max_chars_per_file * 2)
                        decoded = data.decode("utf-8", errors="replace")[:max_chars_per_file]
                    part = f"\n--- TỆP: {name} ---\n{decoded}\n--- HẾT TỆP: {name} ---"
                    content_parts.append(part)
                    total_chars += len(part)
                    read_count += 1
                except Exception:
                    continue

            content_parts.append(f"\n=== HẾT TẬP TIN NÉN ({read_count}/{len(files_to_read)} tệp được nạp) ===")
            return "\n".join(content_parts)
    except Exception as e:
        return f"[Lỗi khi giải nén tệp zip: {str(e)}]"

def read_local_file(path: str, max_chars: int = 5000) -> str:
    """Hỗ trợ đọc file hoặc thư mục bất kỳ từ ổ đĩa (code, text, csv, json, md, zip, folder...)."""
    try:
        clean_path = path.strip().strip('"').strip("'")
        if not os.path.exists(clean_path):
            return f"[Lỗi: Không tìm thấy tệp hoặc thư mục tại đường dẫn: {clean_path}]"
        
        # Nếu là thư mục: Quét toàn bộ thư mục
        if os.path.isdir(clean_path):
            return read_local_directory(clean_path)

        # Nếu là file zip: Giải nén và đọc cây thư mục
        if clean_path.lower().endswith(".zip"):
            return read_zip_archive(clean_path, filename=os.path.basename(clean_path))

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
    attached_content: Optional[str] = None,
    custom_persona_prompt: Optional[str] = None
) -> Generator[str, None, None]:
    """Phát luồng câu trả lời (streaming) từ mô hình ngôn ngữ lớn có hỗ trợ tự động chuyển model dự phòng khi nghẽn token."""
    client, model_name = get_openai_client()
    if not client:
        yield "⚠️ Chưa tìm thấy API Key! Vui lòng kiểm tra file `.env` và cung cấp `GROQ_API_KEY` hoặc `OPENAI_API_KEY`."
        return

    if persona_key == "custom" and custom_persona_prompt and custom_persona_prompt.strip():
        system_instruction = custom_persona_prompt.strip()
    else:
        persona = EXPERT_PERSONAS.get(persona_key, EXPERT_PERSONAS["developer"])
        system_instruction = persona["system_prompt"]
    system_instruction += (
        "\n\n[QUY TẮC ĐẶC BIỆT KHI VIẾT CODE CHO DỰ ÁN]:"
        "\nKhi bạn viết code, tạo file mới hoặc sửa file trong dự án, BẮT BUỘC phải đặt nhãn tên file ngay trước khối code theo đúng định dạng:"
        "\n[FILE: duong_dan/ten_file.ext]"
        "\n```ngon_ngu"
        "\n# code day du..."
        "\n```"
        "\nVí dụ: [FILE: src/main.py] hoặc [FILE: index.html]. Hệ thống sẽ tự động bắt nhãn [FILE: ...] để ghi code trực tiếp vào thư mục dự án trên ổ đĩa máy tính của người dùng."
    )
    system_instruction += (
        "\n\n[QUY TẮC TẠO HÌNH ẢNH HOẶC CHẠY KẾT QUẢ]:"
        "\nKhi người dùng hỏi về hình ảnh, yêu cầu vẽ tranh, tạo ảnh hoặc muốn xem kết quả trực quan (ví dụ: 'chay ra hinh anh', 'vẽ con mèo', 'tạo ảnh...'): BẮT BUỘC bạn phải giải thích ngắn gọn và xuất thẻ [IMAGE: mô tả hình ảnh bằng tiếng Anh hoặc tiếng Việt], ví dụ: [IMAGE: a beautiful futuristic city with flying cars, 4k resolution]. Hệ thống sẽ tự động bắt thẻ [IMAGE: ...] để gọi AI vẽ ảnh và hiển thị ảnh ra ngay lập tức!"
    )

    # Cắt gọn nội dung đính kèm an toàn dưới 5000 ký tự (~1200 tokens) để không bao giờ vượt ngưỡng 8000 TPM
    if attached_content:
        safe_attached = attached_content[:5000]
        if len(attached_content) > 5000:
            safe_attached += "\n...(Đã lược bớt để đảm bảo giới hạn token an toàn)..."
        system_instruction += f"\n\n[DỮ LIỆU/TỆP ĐÍNH KÈM ĐƯỢC CUNG CẤP]:\n{safe_attached}"

    # Giới hạn số lượng tin nhắn gần nhất để tránh phình to ngữ cảnh
    recent_messages = messages[-6:] if len(messages) > 6 else messages
    formatted_messages = [{"role": "system", "content": system_instruction}]
    formatted_messages.extend(recent_messages)

    fallback_models = [model_name, "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
    fallback_models = list(dict.fromkeys([m for m in fallback_models if m]))

    last_error = None
    for attempt_model in fallback_models:
        try:
            stream = client.chat.completions.create(
                model=attempt_model,
                messages=formatted_messages,
                stream=True,
                temperature=0.6,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
            return
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if "413" in err_str or "rate_limit" in err_str or "tpm" in err_str or "tokens" in err_str:
                # Tự động thử model tiếp theo có hạn mức TPM cao hơn
                continue
            else:
                yield f"\n\n❌ Lỗi trong quá trình phản hồi từ AI ({attempt_model}): {str(e)}"
                return

    if last_error:
        yield f"\n\n❌ Lỗi giới hạn tốc độ Groq TPM: Vui lòng đợi 20 giây và thử lại! (Chi tiết: {str(last_error)})"
