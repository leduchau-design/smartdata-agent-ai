"""
Script tự động tạo repo GitHub và push toàn bộ code lên.
"""
import os
import base64
import json
import urllib.request
import urllib.error

TOKEN = "your_github_token_here"
USERNAME = "leduchau-design"
REPO_NAME = "smartdata-agent"
BASE_DIR = r"d:\python\du an"

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "Content-Type": "application/json",
    "User-Agent": "Python-Deploy-Script"
}

# Danh sách file cần push (bỏ qua venv, __pycache__, .env, data/charts)
FILES_TO_PUSH = [
    "frontend/app.py",
    "src/__init__.py",
    "src/agents.py",
    "src/chat_service.py",
    "src/image_service.py",
    "src/main.py",
    "src/tools.py",
    "requirements.txt",
    ".env.example",
    ".gitignore",
    "README.md",
    ".streamlit/config.toml",
    "run_all.bat",
    "run_backend.bat",
    "run_frontend.bat",
    "run_with_ngrok.bat",
]

def api_request(method, url, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

def create_repo():
    print(f"📦 Tạo repo '{REPO_NAME}'...")
    data, status = api_request("POST", "https://api.github.com/user/repos", {
        "name": REPO_NAME,
        "description": "AI Expert Copilot & SmartData Agent - Streamlit App",
        "private": False,
        "auto_init": False
    })
    if status in (201, 422):  # 422 = đã tồn tại
        if status == 422:
            print(f"  ℹ️  Repo đã tồn tại, tiếp tục push files...")
        else:
            print(f"  ✅ Tạo repo thành công!")
        return True
    print(f"  ❌ Lỗi tạo repo: {data}")
    return False

def get_file_sha(path):
    """Lấy SHA của file đã tồn tại trên GitHub (để update)."""
    url = f"https://api.github.com/repos/{USERNAME}/{REPO_NAME}/contents/{path}"
    data, status = api_request("GET", url)
    if status == 200:
        return data.get("sha")
    return None

def push_file(local_path, remote_path):
    full_path = os.path.join(BASE_DIR, local_path.replace("/", os.sep))
    if not os.path.exists(full_path):
        print(f"  ⚠️  Bỏ qua (không tìm thấy): {local_path}")
        return

    with open(full_path, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    sha = get_file_sha(remote_path)
    payload = {
        "message": f"Deploy: {remote_path}",
        "content": content,
    }
    if sha:
        payload["sha"] = sha

    url = f"https://api.github.com/repos/{USERNAME}/{REPO_NAME}/contents/{remote_path}"
    data, status = api_request("PUT", url, payload)
    if status in (200, 201):
        print(f"  ✅ {remote_path}")
    else:
        print(f"  ❌ Lỗi {remote_path}: {data.get('message', data)}")

def create_src_init():
    """Tạo src/__init__.py nếu chưa có."""
    init_path = os.path.join(BASE_DIR, "src", "__init__.py")
    if not os.path.exists(init_path):
        with open(init_path, "w") as f:
            f.write("")

if __name__ == "__main__":
    print("🚀 Bắt đầu deploy lên GitHub...\n")
    create_src_init()

    if not create_repo():
        exit(1)

    print(f"\n📤 Đang push files lên github.com/{USERNAME}/{REPO_NAME}...\n")
    for file_path in FILES_TO_PUSH:
        push_file(file_path, file_path)

    print(f"\n🎉 Xong! Repo: https://github.com/{USERNAME}/{REPO_NAME}")
    print(f"\n👉 Bước tiếp theo: Deploy lên Streamlit Cloud tại https://share.streamlit.io")
