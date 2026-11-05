import os
import sys
import json
import re
import subprocess
from typing import List, Dict, Any, Optional, Tuple

PROJECTS_METADATA_FILE = os.path.abspath("data/projects_history.json")
SUPPORTED_CODE_EXTS = {
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

def load_projects_history() -> List[Dict[str, str]]:
    """Đọc lịch sử các dự án đã từng mở."""
    if not os.path.exists(PROJECTS_METADATA_FILE):
        return []
    try:
        with open(PROJECTS_METADATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_project_to_history(project_path: str, project_name: str = "") -> None:
    """Lưu dự án vào lịch sử."""
    clean_p = os.path.abspath(project_path.strip().strip('"').strip("'"))
    name = project_name.strip() or os.path.basename(clean_p) or "Dự án không tên"
    history = load_projects_history()
    # Loại bỏ bản ghi cũ nếu trùng path
    history = [p for p in history if os.path.abspath(p.get("path", "")) != clean_p]
    history.insert(0, {"name": name, "path": clean_p})
    # Giữ tối đa 15 dự án gần nhất
    history = history[:15]
    try:
        os.makedirs(os.path.dirname(PROJECTS_METADATA_FILE), exist_ok=True)
        with open(PROJECTS_METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def list_project_files(folder_path: str, max_files: int = 150) -> List[str]:
    """Liệt kê danh sách các tệp code/tài liệu trong thư mục dự án."""
    clean_p = folder_path.strip().strip('"').strip("'")
    if not os.path.exists(clean_p) or not os.path.isdir(clean_p):
        return []
    
    file_list = []
    for root, dirs, files in os.walk(clean_p):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        rel_dir = os.path.relpath(root, clean_p)
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_CODE_EXTS or ext in [".txt", ".md", ".json"]:
                rel_f = os.path.normpath(os.path.join(rel_dir, f)) if rel_dir != "." else f
                file_list.append(rel_f)
                if len(file_list) >= max_files:
                    return file_list
    return file_list

def create_quick_start_project() -> Tuple[str, str]:
    """Tạo một dự án mẫu Quick Start hoàn chỉnh trong data/projects/quick_start_demo."""
    target_dir = os.path.abspath("data/projects/quick_start_demo")
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(os.path.join(target_dir, "src"), exist_ok=True)

    # 1. main.py
    main_py = os.path.join(target_dir, "src", "main.py")
    if not os.path.exists(main_py):
        with open(main_py, "w", encoding="utf-8") as f:
            f.write('''# Quick Start Demo Project
def calculate_summary(items: list[dict]) -> dict:
    total_val = sum(item.get("value", 0) for item in items)
    count = len(items)
    avg = total_val / count if count > 0 else 0
    return {"total": total_val, "count": count, "average": avg}

if __name__ == "__main__":
    sample_data = [
        {"name": "Sản phẩm A", "value": 150},
        {"name": "Sản phẩm B", "value": 280},
        {"name": "Sản phẩm C", "value": 90}
    ]
    res = calculate_summary(sample_data)
    print("Ket qua phan tich:", res)
''')

    # 2. README.md
    readme_md = os.path.join(target_dir, "README.md")
    if not os.path.exists(readme_md):
        with open(readme_md, "w", encoding="utf-8") as f:
            f.write('''# Quick Start Demo Project
Dự án khởi động nhanh cho SmartData AI Agent.
Bạn có thể yêu cầu AI viết thêm code, tối ưu hoặc tạo thêm các module mới vào thư mục này!
''')

    save_project_to_history(target_dir, "Quick Start Demo")
    return target_dir, "Quick Start Demo"

def write_file_to_project(folder_path: str, relative_file_path: str, content: str) -> Tuple[bool, str, str]:
    """Ghi nội dung code trực tiếp vào file trong thư mục dự án."""
    try:
        clean_dir = os.path.abspath(folder_path.strip().strip('"').strip("'"))
        if not os.path.exists(clean_dir):
            os.makedirs(clean_dir, exist_ok=True)

        # Chuẩn hóa relative path
        rel_clean = relative_file_path.strip().strip('"').strip("'").strip("/").strip("\\")
        # Tránh escape khỏi thư mục dự án
        target_full_path = os.path.abspath(os.path.join(clean_dir, rel_clean))
        if not target_full_path.startswith(clean_dir):
            return False, "", "Lỗi bảo mật: Đường dẫn file nằm ngoài thư mục dự án!"

        # Tự động tạo thư mục cha nếu chưa tồn tại
        os.makedirs(os.path.dirname(target_full_path), exist_ok=True)

        with open(target_full_path, "w", encoding="utf-8") as f:
            f.write(content)

        return True, target_full_path, f"Đã ghi thành công vào `{rel_clean}`"
    except Exception as e:
        return False, "", f"Lỗi khi ghi file: {str(e)}"

def parse_files_from_ai_reply(reply_text: str) -> List[Dict[str, Any]]:
    """Phân tích và bóc tách các tệp code được AI sinh ra trong phản hồi."""
    if not reply_text:
        return []
    
    # Chuẩn hóa ngắt dòng để tương thích tốt trên cả Windows, Linux và macOS
    norm_text = reply_text.replace("\r\n", "\n").replace("\r", "\n")
    parsed_files = []
    
    # 1. Pattern chính: [FILE: relative/path/to/file.ext] kèm theo khối code ```lang ... ```
    pattern_bracket = re.compile(
        r'\[FILE:\s*`?([^\s`\]]+)`?\]\s*\n*```(?:[a-zA-Z0-9_\-\+\.]+)?\n(.*?)```',
        re.DOTALL
    )
    for match in pattern_bracket.finditer(norm_text):
        fname = match.group(1).strip("`'\" \t")
        code_content = match.group(2)
        parsed_files.append({
            "file_path": fname,
            "content": code_content,
            "lines": len(code_content.splitlines())
        })

    # 2. Pattern phụ: ### 📄 File: <path> hoặc ### File: <path> kèm ```lang ... ```
    pattern_heading = re.compile(
        r'###\s*(?:📄\s*)?File:\s*`?([^\s`\n]+)`?\s*\n*```(?:[a-zA-Z0-9_\-\+\.]+)?\n(.*?)```',
        re.DOTALL
    )
    for match in pattern_heading.finditer(norm_text):
        fname = match.group(1).strip("`'\" \t")
        code_content = match.group(2)
        # Tránh trùng lặp nếu đã parse ở pattern 1
        if not any(f["file_path"] == fname for f in parsed_files):
            parsed_files.append({
                "file_path": fname,
                "content": code_content,
                "lines": len(code_content.splitlines())
            })

    # 3. Pattern trong comment dòng đầu tiên: ```lang \n # filepath: <path>
    pattern_filepath_comment = re.compile(
        r'```(?:[a-zA-Z0-9_\-\+\.]+)?\n(?:#|//)\s*(?:filepath|file):\s*`?([^\s`\n]+)`?\n(.*?)```',
        re.DOTALL
    )
    for match in pattern_filepath_comment.finditer(norm_text):
        fname = match.group(1).strip("`'\" \t")
        code_content = match.group(2)
        if not any(f["file_path"] == fname for f in parsed_files):
            parsed_files.append({
                "file_path": fname,
                "content": code_content,
                "lines": len(code_content.splitlines())
            })

    return parsed_files

def open_folder_in_explorer(folder_path: str) -> bool:
    """Mở thư mục trong Windows Explorer."""
    try:
        clean_p = os.path.abspath(folder_path.strip().strip('"').strip("'"))
        if os.path.exists(clean_p):
            if sys.platform == "win32":
                os.startfile(clean_p)
                return True
            else:
                subprocess.Popen(["xdg-open", clean_p])
                return True
    except Exception:
        pass
    return False

def parse_images_from_ai_reply(reply_text: str) -> List[str]:
    """Bóc tách các yêu cầu tạo ảnh từ thẻ [IMAGE: <prompt>] trong câu trả lời."""
    prompts = []
    pattern = re.compile(r'\[IMAGE:\s*(.*?)\]', re.DOTALL)
    for m in pattern.finditer(reply_text):
        p = m.group(1).strip()
        if p:
            prompts.append(p)
    return prompts

def run_python_file(folder_path: str, relative_file_path: str, timeout: int = 15) -> Tuple[bool, str]:
    """Chạy trực tiếp file Python trong thư mục dự án và lấy kết quả output."""
    try:
        clean_dir = os.path.abspath(folder_path.strip().strip('"').strip("'"))
        rel_clean = relative_file_path.strip().strip('"').strip("'").strip("/").strip("\\")
        target_path = os.path.abspath(os.path.join(clean_dir, rel_clean))
        if not os.path.exists(target_path):
            return False, f"Không tìm thấy file: {rel_clean}"

        py_exec = sys.executable
        res = subprocess.run(
            [py_exec, target_path],
            cwd=clean_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace"
        )
        stdout = res.stdout.strip()
        stderr = res.stderr.strip()
        if res.returncode == 0:
            out = stdout if stdout else "(Chương trình chạy hoàn tất thành công, không có console output)"
            return True, out
        else:
            err = stderr if stderr else stdout
            return False, f"Lỗi thực thi (Exit code {res.returncode}):\n{err}"
    except subprocess.TimeoutExpired:
        return False, "Lỗi: Quá thời gian thực thi (Timeout 15 giây)!"
    except Exception as e:
        return False, f"Lỗi khi chạy file: {str(e)}"
