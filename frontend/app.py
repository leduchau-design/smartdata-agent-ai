import os
import sys
import re
import streamlit as st

# Đảm bảo import được module từ thư mục src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import importlib
try:
    import src.chat_service
    importlib.reload(src.chat_service)
except Exception:
    pass

try:
    import src.project_service
    importlib.reload(src.project_service)
except Exception:
    pass

from src.chat_service import (
    EXPERT_PERSONAS,
    stream_chat_response,
    read_local_file,
    read_zip_archive,
    select_folder_dialog
)

# Import an toàn từ src.project_service kèm fallback dự phòng nếu module bị lock
try:
    from src.project_service import (
        load_projects_history,
        save_project_to_history,
        list_project_files,
        create_quick_start_project,
        write_file_to_project,
        parse_files_from_ai_reply,
        parse_images_from_ai_reply,
        run_python_file,
        open_folder_in_explorer
    )
except ImportError:
    from src.project_service import (
        load_projects_history,
        save_project_to_history,
        list_project_files,
        create_quick_start_project,
        write_file_to_project,
        parse_files_from_ai_reply,
        open_folder_in_explorer
    )
    def parse_images_from_ai_reply(reply_text: str):
        prompts = []
        pattern = re.compile(r'\[IMAGE:\s*(.*?)\]', re.DOTALL)
        for m in pattern.finditer(reply_text):
            p = m.group(1).strip()
            if p:
                prompts.append(p)
        return prompts

    def run_python_file(folder_path: str, relative_file_path: str, timeout: int = 15):
        import subprocess
        try:
            clean_dir = os.path.abspath(folder_path.strip().strip('"').strip("'"))
            rel_clean = relative_file_path.strip().strip('"').strip("'").strip("/").strip("\\")
            target_path = os.path.abspath(os.path.join(clean_dir, rel_clean))
            if not os.path.exists(target_path):
                return False, f"Không tìm thấy file: {rel_clean}"
            res = subprocess.run([sys.executable, target_path], cwd=clean_dir, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
            return res.returncode == 0, (res.stdout.strip() if res.stdout.strip() else res.stderr.strip())
        except Exception as e:
            return False, str(e)

from src.image_service import generate_ai_art_advanced, AVAILABLE_MODELS

st.set_page_config(
    page_title="AI Expert Copilot & Data Intelligence",
    layout="wide",
    page_icon="🧠"
)

# Đảm bảo các thư mục cần thiết luôn tồn tại
os.makedirs("data", exist_ok=True)
os.makedirs("data/charts", exist_ok=True)

# ==========================================
# CSS NÂNG CAO CHO GIAO DIỆN ĐẸP HƠN
# ==========================================
st.markdown("""
<style>
/* Card hiển thị ảnh AI */
.ai-image-card {
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,0.18);
    margin-bottom: 16px;
}
/* Style cho model badge */
.model-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
    background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
    color: white;
    margin-bottom: 8px;
}
/* Prompt suggestion buttons */
.stButton > button {
    border-radius: 8px;
    transition: all 0.2s;
}
/* Chat input - để Streamlit tự xử lý layout, không bị sidebar che */
.stChatInput textarea {
    border-radius: 12px !important;
}
/* Thêm padding dưới cùng để tin nhắn không bị che bởi input */
.stChatMessage:last-of-type {
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# Khởi tạo trạng thái phiên làm việc (Session State)
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": (
                "👋 **Xin chào! Tôi là Trợ lý AI Chuyên gia.**\n\n"
                "Tôi có thể hỗ trợ bạn sâu sắc về **lập trình (viết code, debug, thiết kế hệ thống)**, "
                "**khoa học máy tính, phân tích dữ liệu, kinh doanh** và bất kỳ lĩnh vực nào bạn quan tâm.\n\n"
                "👉 Bạn có thể đặt câu hỏi tự do ngay bên dưới, hoặc đính kèm tệp/đường dẫn file ở thanh bên trái nếu cần tôi đọc code/tài liệu!"
            )
        }
    ]

if "generated_images" not in st.session_state:
    st.session_state.generated_images = []  # Lưu lịch sử ảnh đã tạo

if "active_project" not in st.session_state:
    _history = load_projects_history()
    if _history and os.path.exists(_history[0].get("path", "")):
        st.session_state.active_project = _history[0]
    else:
        st.session_state.active_project = None

if "auto_write_code" not in st.session_state:
    st.session_state.auto_write_code = True  # Mặc định tự động ghi code vào folder

if "show_new_project_modal" not in st.session_state:
    st.session_state.show_new_project_modal = False

if "temp_project_path" not in st.session_state:
    st.session_state.temp_project_path = ""

# ==========================================
# SIDEBAR: CẤU HÌNH & TÙY CHỌN CHUYÊN GIA
# ==========================================
with st.sidebar:
    st.title("⚙️ Cấu Hình Chuyên Gia")
    
    # Nút xóa lịch sử chat
    if st.button("🔄 Bắt đầu cuộc trò chuyện mới", use_container_width=True):
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": "✨ Đã bắt đầu cuộc trò chuyện mới! Hãy hỏi tôi bất cứ điều gì bạn cần."
            }
        ]
        st.rerun()

    st.markdown("---")
    st.subheader("🎭 Chọn Lĩnh Vực Chuyên Môn:")
    persona_options = {
        "developer": "💻 Kỹ Sư Lập Trình & Kiến Trúc Phần Mềm",
        "polymath": "🧠 Chuyên Gia Đa Năng Toàn Diện",
        "data_scientist": "📊 Nhà Khoa Học Dữ Liệu & ML",
        "business": "📈 Cố Vấn Chiến Lược & Kinh Doanh",
        "custom": "✨ Tùy Chỉnh Vai Trò..."
    }
    selected_persona_key = st.selectbox(
        "AI sẽ ứng xử theo phong cách:",
        options=list(persona_options.keys()),
        format_func=lambda k: persona_options[k]
    )

    custom_persona_prompt = None
    if selected_persona_key == "custom":
        custom_persona_prompt = st.text_area(
            "Mô tả vai trò chuyên gia bạn muốn:",
            value="Bạn là một chuyên gia tư vấn thiết kế giải pháp phần mềm cấp cao.",
            placeholder="Ví dụ: Bạn là một chuyên gia DevOps am hiểu Docker, K8s..."
        )
    else:
        st.caption(f"ℹ️ *{EXPERT_PERSONAS.get(selected_persona_key, {}).get('desc', '')}*")

    st.markdown("---")
    st.subheader("📁 QUẢN LÝ DỰ ÁN (PROJECTS)")

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        if st.button("📁+ New Project", use_container_width=True, help="Tạo hoặc mở dự án từ thư mục máy tính"):
            st.session_state.show_new_project_modal = not st.session_state.show_new_project_modal
    with col_p2:
        if st.button("⚡ Quick Start", use_container_width=True, help="Tạo nhanh dự án mẫu Quick Start"):
            qpath, qname = create_quick_start_project()
            st.session_state.active_project = {"name": qname, "path": qpath}
            st.toast(f"✨ Đã khởi tạo dự án mẫu: {qname}!", icon="🚀")
            st.rerun()

    # Form nhập / chọn New Project
    if st.session_state.show_new_project_modal:
        with st.container(border=True):
            st.markdown("##### 📁 Tạo / Mở Dự Án Mới")
            p_name = st.text_input("Tên dự án:", placeholder="Ví dụ: Backend App, My Project...")

            # Gợi ý thư mục nhanh phổ biến
            st.caption("📌 **Chọn nhanh thư mục phổ biến:**")
            quick_dirs = {
                "🖥️ Desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
                "📄 Documents": os.path.join(os.path.expanduser("~"), "Documents"),
                "📂 Downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
                "🐍 D:\\python": "D:\\python",
                "📁 C:\\Projects": "C:\\Projects",
            }
            q_cols = st.columns(3)
            for i, (label, qpath) in enumerate(quick_dirs.items()):
                with q_cols[i % 3]:
                    if st.button(label, key=f"quick_dir_{i}", use_container_width=True):
                        if os.path.exists(qpath):
                            st.session_state.temp_project_path = qpath
                        else:
                            st.session_state.temp_project_path = qpath
                        st.rerun()

            st.caption(
                "💡 **Cách lấy đường dẫn nhanh trên Windows:**  \n"
                "Mở File Explorer → vào thư mục muốn chọn → "
                "nhấn vào **thanh địa chỉ** trên cùng → **Ctrl+C** → paste vào ô bên dưới."
            )

            p_path = st.text_input(
                "📂 Đường dẫn thư mục dự án (paste vào đây):",
                value=st.session_state.temp_project_path,
                placeholder="Ví dụ: D:\\python\\my-project hoặc C:\\Users\\Admin\\Desktop\\MyApp"
            )

            # Nếu đã có path hợp lệ → preview tên thư mục
            if p_path.strip() and os.path.exists(p_path.strip().strip('"').strip("'")):
                st.success(f"✅ Thư mục hợp lệ: `{os.path.basename(p_path.strip().strip(chr(34)).strip(chr(39)))}`")
            elif p_path.strip():
                st.info("📁 Thư mục chưa tồn tại — sẽ được tạo mới khi bấm Mở Dự Án.")

            col_sub1, col_sub2 = st.columns(2)
            with col_sub1:
                if st.button("✅ Mở Dự Án", use_container_width=True, type="primary"):
                    if p_path.strip():
                        clean_dir = os.path.abspath(p_path.strip().strip('"').strip("'"))
                        os.makedirs(clean_dir, exist_ok=True)
                        eff_name = p_name.strip() or os.path.basename(clean_dir) or "Dự án mới"
                        save_project_to_history(clean_dir, eff_name)
                        st.session_state.active_project = {"name": eff_name, "path": clean_dir}
                        st.session_state.show_new_project_modal = False
                        st.session_state.temp_project_path = ""
                        st.toast(f"🎉 Đã kết nối với dự án: {eff_name}!", icon="📁")
                        st.rerun()
                    else:
                        st.error("Vui lòng nhập đường dẫn thư mục!")
            with col_sub2:
                if st.button("Đóng", use_container_width=True):
                    st.session_state.show_new_project_modal = False
                    st.rerun()

    # Danh sách các dự án gần đây
    proj_history = load_projects_history()
    if proj_history:
        history_names = [f"📁 {p['name']}" for p in proj_history]
        active_idx = 0
        if st.session_state.active_project:
            for idx, p in enumerate(proj_history):
                if os.path.abspath(p.get("path", "")) == os.path.abspath(st.session_state.active_project.get("path", "")):
                    active_idx = idx
                    break
        selected_hist_idx = st.selectbox(
            "Dự án gần đây:",
            options=range(len(proj_history)),
            index=active_idx,
            format_func=lambda i: history_names[i]
        )
        if st.session_state.active_project != proj_history[selected_hist_idx]:
            st.session_state.active_project = proj_history[selected_hist_idx]
            st.rerun()

    # Thẻ thông tin dự án đang chọn (Active Project)
    attached_text = None
    if st.session_state.active_project:
        act_proj = st.session_state.active_project
        act_path = act_proj.get("path", "")
        with st.container(border=True):
            st.markdown(f"🏷️ **Dự án:** `{act_proj.get('name')}`")
            st.caption(f"📂 `{act_path}`")
            
            c_exp, c_rel = st.columns([1, 1])
            with c_exp:
                if st.button("🖥️ Mở Explorer", use_container_width=True, help="Mở thư mục trên máy tính"):
                    open_folder_in_explorer(act_path)
            with c_rel:
                if st.button("🔄 Quét lại", use_container_width=True, help="Quét lại file dự án"):
                    st.rerun()

            p_files = list_project_files(act_path)
            with st.expander(f"🌳 Danh sách tệp ({len(p_files)} tệp)", expanded=False):
                if p_files:
                    for pf in p_files:
                        st.text(f"📄 {pf}")
                else:
                    st.caption("Thư mục hiện đang trống. Hãy yêu cầu AI viết code!")

        # Toggle tự động ghi code vào folder
        st.session_state.auto_write_code = st.toggle(
            "⚡ Tự động ghi code vào thư mục",
            value=st.session_state.auto_write_code,
            help="Bật chế độ này: Bất kỳ file nào AI sinh ra sẽ được tự động ghi thẳng vào thư mục dự án trên máy tính!"
        )

        # Nạp toàn bộ code dự án vào ngữ cảnh của AI
        if os.path.exists(act_path):
            attached_text = read_local_file(act_path)
    else:
        st.info("💡 Hãy bấm **📁+ New Project** hoặc **⚡ Quick Start** để chọn thư mục làm việc cho AI!")

    # Khu vực tải thêm tệp/zip phụ ngoài lề
    with st.expander("📎 Đính kèm tệp / zip ngoài lề (Tùy chọn)", expanded=False):
        uploaded_extra_files = st.file_uploader(
            "Tải file đính kèm thêm:",
            type=["zip", "py", "js", "jsx", "ts", "tsx", "html", "css", "json", "csv", "txt", "md", "sql", "yaml", "yml", "env", "sh", "bat", "ps1", "java", "cpp", "c", "cs", "go", "rs", "php", "xml", "toml"],
            accept_multiple_files=True,
            key="extra_files_uploader"
        )
        if uploaded_extra_files:
            extra_parts = []
            for up_f in uploaded_extra_files:
                if up_f.name.lower().endswith(".zip"):
                    extra_parts.append(read_zip_archive(up_f.read(), filename=up_f.name))
                else:
                    raw_b = up_f.read().decode("utf-8", errors="replace")
                    extra_parts.append(f"=== TỆP PHỤ: {up_f.name} ===\n{raw_b[:8000]}\n=== HẾT TỆP PHỤ ===")
            if extra_parts:
                extra_str = "\n\n".join(extra_parts)
                attached_text = f"{attached_text}\n\n{extra_str}" if attached_text else extra_str
                st.success(f"📎 Đã nhận {len(uploaded_extra_files)} tệp phụ!")

    # Bản xem trước ngữ cảnh nạp
    if attached_text:
        with st.expander("👀 Xem trước ngữ cảnh AI nhận được", expanded=False):
            st.text(attached_text[:2500] + ("\n...(Nội dung còn tiếp)..." if len(attached_text) > 2500 else ""))

    st.markdown("---")
    st.markdown("⚡ **Trạng thái AI:** Groq High-Speed LLM (`openai/gpt-oss-120b`)")
    st.markdown("🌐 **Backend:** FastAPI sẵn sàng trên cổng `8000`")
    st.markdown("🎨 **Image AI:** Pollinations AI (FLUX Models)")

# ==========================================
# KHU VỰC CHÍNH: 3 TABS TRẢI NGHIỆM
# ==========================================
tab_chat, tab_data_3d, tab_image_gen = st.tabs([
    "💬 Trò Chuyện Chuyên Gia (AI Copilot Mở)",
    "🧊 Phân Tích Bảng & Mô Hình 3D (SmartData Agent)",
    "🎨 Tạo Ảnh AI Theo Yêu Cầu (Text-to-Image)"
])

# ------------------------------------------
# TAB 1: TRÒ CHUYỆN MỞ VỚI CHUYÊN GIA
# ------------------------------------------
with tab_chat:
    st.markdown("### 💬 Trò Chuyện & Làm Việc Với Chuyên Gia AI")
    st.markdown("Trao đổi tự do về **lập trình, phân tích vấn đề, giải thuật, viết tài liệu** hoặc bất kỳ chuyên môn nào bạn muốn.")

    # Hiển thị lịch sử chat
    for msg_idx, msg in enumerate(st.session_state.chat_messages):
        with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"])

            # Hiển thị hình ảnh nếu có trong tin nhắn AI
            if msg.get("role") == "assistant" and msg.get("images"):
                for img_p in msg.get("images", []):
                    if os.path.exists(img_p):
                        st.image(img_p, caption="🎨 Ảnh AI tạo theo yêu cầu", use_container_width=True)
                        with open(img_p, "rb") as f_img:
                            st.download_button("📥 Tải ảnh về máy", data=f_img, file_name=os.path.basename(img_p), mime="image/jpeg", key=f"dl_img_{msg_idx}_{os.path.basename(img_p)}")

            # Nếu là phản hồi của AI và có tệp code
            if msg.get("role") == "assistant":
                msg_files = msg.get("files") or parse_files_from_ai_reply(msg["content"])
                if msg_files and st.session_state.active_project:
                    act_path = st.session_state.active_project.get("path")
                    with st.container(border=True):
                        st.markdown(f"📦 **Phát hiện {len(msg_files)} tệp mã nguồn cho dự án:**")
                        col_w_all, _ = st.columns([1, 1])
                        with col_w_all:
                            if st.button("⚡ Ghi tất cả vào thư mục", key=f"btn_write_all_{msg_idx}"):
                                for mf in msg_files:
                                    write_file_to_project(act_path, mf["file_path"], mf["content"])
                                st.toast(f"🎉 Đã lưu {len(msg_files)} tệp vào thư mục dự án!", icon="💾")
                                st.success(f"🎉 Đã ghi thành công {len(msg_files)} tệp vào: `{act_path}`")
                                st.rerun()

                        for f_idx, mf in enumerate(msg_files):
                            c1, c2, c3 = st.columns([3, 1, 1])
                            with c1:
                                st.markdown(f"📄 **`{mf['file_path']}`** ({mf['lines']} dòng)")
                            with c2:
                                if st.button("💾 Ghi file", key=f"btn_write_{msg_idx}_{f_idx}"):
                                    ok, fp, err = write_file_to_project(act_path, mf["file_path"], mf["content"])
                                    if ok:
                                        st.toast(f"✅ Đã ghi `{mf['file_path']}`", icon="💾")
                                        st.success(f"✅ Đã lưu vào: `{fp}`")
                                    else:
                                        st.error(err)
                            with c3:
                                # Nút chạy file nếu là file Python
                                if mf["file_path"].endswith(".py"):
                                    if st.button("▶️ Chạy", key=f"btn_run_{msg_idx}_{f_idx}", help="Chạy file Python này ngay lập tức"):
                                        # Ghi file trước khi chạy để đảm bảo phiên bản mới nhất
                                        write_file_to_project(act_path, mf["file_path"], mf["content"])
                                        ok_run, out_run = run_python_file(act_path, mf["file_path"])
                                        st.session_state[f"run_out_{msg_idx}_{f_idx}"] = out_run

                            # Hiển thị console output nếu đã bấm chạy
                            if f"run_out_{msg_idx}_{f_idx}" in st.session_state:
                                with st.expander(f"🖥️ Terminal Output: `{mf['file_path']}`", expanded=True):
                                    st.code(st.session_state[f"run_out_{msg_idx}_{f_idx}"], language="bash")
                elif msg_files and not st.session_state.active_project:
                    st.caption("ℹ️ *Để ghi và chạy các tệp này trên máy tính, hãy chọn hoặc tạo dự án ở thanh bên trái.*")

    # Gợi ý nhanh nếu đoạn chat còn mới
    if len(st.session_state.chat_messages) <= 1:
        st.write("💡 **Gợi ý yêu cầu nhanh:**")
        col_s1, col_s2, col_s3 = st.columns(3)
        prompt_preset = None
        with col_s1:
            if st.button("🛠️ Viết ứng dụng CRUD bằng Python"):
                prompt_preset = "Hãy hướng dẫn và viết code mẫu xây dựng một ứng dụng REST API CRUD hoàn chỉnh bằng FastAPI và SQLite, tuân thủ Clean Architecture."
        with col_s2:
            if st.button("🎨 Tạo một bức tranh thành phố tương lai"):
                prompt_preset = "Hãy tạo hình ảnh một thành phố tương lai cyberpunk với xe bay và ánh đèn neon rực rỡ, kèm mô tả thiết kế hệ thống."
        with col_s3:
            if st.button("📊 Phân tích cách xử lý dữ liệu lớn"):
                prompt_preset = "So sánh hiệu năng giữa Polars và Pandas khi xử lý tập dữ liệu lớn hàng chục gigabyte."

        if prompt_preset:
            st.session_state.chat_messages.append({"role": "user", "content": prompt_preset})
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(prompt_preset)

            with st.chat_message("assistant", avatar="🤖"):
                chat_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages]
                response_stream = stream_chat_response(
                    messages=chat_history,
                    persona_key=selected_persona_key,
                    attached_content=attached_text,
                    custom_persona_prompt=custom_persona_prompt
                )
                full_reply = st.write_stream(response_stream)
                gen_files = parse_files_from_ai_reply(full_reply)
                
                # Tự động ghi code nếu bật auto_write_code
                if gen_files and st.session_state.active_project and st.session_state.auto_write_code:
                    act_p = st.session_state.active_project.get("path")
                    written_names = []
                    for gf in gen_files:
                        ok, fp, err = write_file_to_project(act_p, gf["file_path"], gf["content"])
                        if ok:
                            written_names.append(gf["file_path"])
                    if written_names:
                        st.toast(f"⚡ Đã tự động lưu {len(written_names)} file vào thư mục!", icon="💾")
                        st.success(f"⚡ **Đã tự động lưu {len(written_names)} file vào thư mục:** `{', '.join(written_names)}`")

                # Kiểm tra và tạo ảnh nếu có yêu cầu
                saved_imgs = []
                img_prompts = parse_images_from_ai_reply(full_reply)
                if not img_prompts and ("thành phố tương lai" in prompt_preset or "hình ảnh" in prompt_preset):
                    img_prompts = [prompt_preset]
                for ip in img_prompts:
                    with st.spinner("🎨 Đang kết nối AI sinh hình ảnh..."):
                        created_img = generate_ai_art_advanced(ip)
                        if created_img:
                            saved_imgs.append(created_img)
                            st.image(created_img, caption="🎨 Ảnh AI tạo theo yêu cầu", use_container_width=True)

                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": full_reply,
                    "files": gen_files,
                    "images": saved_imgs
                })
            st.rerun()

    # Khung nhập chat trực tiếp
    user_input = st.chat_input("Nhập câu hỏi, yêu cầu viết code, tạo ảnh hoặc chạy kết quả...")
    if user_input:
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(user_input)

        # AI trả lời với hiệu ứng Streaming thời gian thực
        with st.chat_message("assistant", avatar="🤖"):
            chat_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages]
            response_stream = stream_chat_response(
                messages=chat_history,
                persona_key=selected_persona_key,
                attached_content=attached_text,
                custom_persona_prompt=custom_persona_prompt
            )
            full_reply = st.write_stream(response_stream)
            gen_files = parse_files_from_ai_reply(full_reply)

            # Tự động ghi code nếu bật auto_write_code
            if gen_files and st.session_state.active_project and st.session_state.auto_write_code:
                act_p = st.session_state.active_project.get("path")
                written_names = []
                for gf in gen_files:
                    ok, fp, err = write_file_to_project(act_p, gf["file_path"], gf["content"])
                    if ok:
                        written_names.append(gf["file_path"])
                if written_names:
                    st.toast(f"⚡ Đã tự động lưu {len(written_names)} file vào thư mục!", icon="💾")
                    st.success(f"⚡ **Đã tự động lưu {len(written_names)} file vào thư mục:** `{', '.join(written_names)}`")

            # Kiểm tra và tạo hình ảnh nếu người dùng hỏi hoặc AI xuất thẻ [IMAGE: ...]
            saved_imgs = []
            img_prompts = parse_images_from_ai_reply(full_reply)
            u_lower = user_input.lower()
            if not img_prompts and ("hinh anh" in u_lower or "hình ảnh" in u_lower or "tạo ảnh" in u_lower or "tao anh" in u_lower or "vẽ" in u_lower or "ve anh" in u_lower):
                img_prompts = [user_input]

            for ip in img_prompts:
                with st.spinner("🎨 Đang gọi AI vẽ và hiển thị hình ảnh trực tiếp..."):
                    created_img = generate_ai_art_advanced(ip)
                    if created_img:
                        saved_imgs.append(created_img)
                        st.image(created_img, caption="🎨 Ảnh AI tạo theo yêu cầu", use_container_width=True)

            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": full_reply,
                "files": gen_files,
                "images": saved_imgs
            })
            st.rerun()


# ------------------------------------------
# TAB 2: PHÂN TÍCH FILE CSV & VẼ BIỂU ĐỒ 3D
# ------------------------------------------
with tab_data_3d:
    st.markdown("### 🧊 Phân Tích File Dữ Liệu Bảng & Dựng Mô Hình 3D Nổi Khối")
    st.markdown("Dành cho bài toán xử lý file số liệu bảng (CSV) với công cụ tính toán Polars và tự động vẽ biểu đồ 3D / 2D.")

    csv_upload = st.file_uploader("Tải lên file dữ liệu CSV cần phân tích:", type=["csv"], key="csv_analysis_uploader")
    if csv_upload is not None:
        csv_path = os.path.abspath(os.path.join("data", csv_upload.name))
        with open(csv_path, "wb") as f_csv:
            f_csv.write(csv_upload.getbuffer())
        st.success(f"✅ Đã nhận file CSV: `{csv_upload.name}`")

        st.write("✨ **Gợi ý yêu cầu nhanh:**")
        col1, col2, col3, col4 = st.columns(4)
        quick_analysis = None
        with col1:
            if st.button("🧊 Vẽ biểu đồ 3D cho file này", key="btn_3d"):
                quick_analysis = "Hãy vẽ biểu đồ 3D thể hiện dữ liệu trong file này giúp tôi"
        with col2:
            if st.button("📊 Phân tích & vẽ biểu đồ cột 2D", key="btn_2d"):
                quick_analysis = "Hãy phân tích tổng hợp dữ liệu và vẽ biểu đồ cột"
        with col3:
            if st.button("🥧 Vẽ biểu đồ tròn cơ cấu", key="btn_pie"):
                quick_analysis = "Hãy phân tích và vẽ biểu đồ tròn tỷ trọng"
        with col4:
            if st.button("🏆 Xem Top 5 cao nhất", key="btn_top5"):
                quick_analysis = "Liệt kê top 5 dòng có số liệu cao nhất và nhận xét ngắn gọn"

        def_val = quick_analysis if quick_analysis else ""
        analysis_query = st.text_input(
            "Nhập yêu cầu phân tích dữ liệu bằng tiếng Việt:",
            value=def_val,
            placeholder="Ví dụ: 'Vẽ mô hình 3D doanh thu', 'Top 5 phòng ban chi phí cao nhất'...",
            key="analysis_input_query"
        )

        if st.button("🚀 Kích hoạt Agent Phân Tích & Dựng Hình Ảnh", key="btn_trigger_analysis") or (quick_analysis is not None):
            if analysis_query:
                with st.spinner("🤖 AI Crew đang đọc dữ liệu bằng Polars, tính toán và dựng mô hình..."):
                    try:
                        from src.agents import create_analysis_crew
                        crew = create_analysis_crew(csv_path, analysis_query)
                        result = crew.kickoff()
                        raw_res = str(result)
                        st.subheader("📋 Kết quả phân tích từ AI:")

                        # Bóc tách thẻ hình ảnh
                        chart_3d_match = re.search(r'\[CHART_3D:\s*(.*?)\]', raw_res)
                        chart_2d_match = re.search(r'\[CHART:\s*(.*?)\]', raw_res)
                        clean_txt = re.sub(r'\[CHART(_3D)?:\s*.*?\]', '', raw_res).strip()
                        st.markdown(clean_txt)

                        # Hiển thị biểu đồ 3D
                        chart_3d_p = None
                        if chart_3d_match and os.path.exists(chart_3d_match.group(1).strip()):
                            chart_3d_p = chart_3d_match.group(1).strip()
                        elif "3d" in analysis_query.lower() and os.path.exists(os.path.abspath("data/charts/latest_3d_chart.png")):
                            chart_3d_p = os.path.abspath("data/charts/latest_3d_chart.png")

                        if chart_3d_p and os.path.exists(chart_3d_p):
                            st.subheader("🧊 Hình ảnh Biểu đồ 3D Không Gian Ba Chiều:")
                            st.image(chart_3d_p, caption="Mô hình 3D nổi khối và góc nhìn đa chiều được AI tự động tạo", use_container_width=True)
                            with open(chart_3d_p, "rb") as f3:
                                st.download_button("📥 Tải xuống hình ảnh 3D (PNG)", data=f3, file_name="bieu_do_3d.png", mime="image/png")

                        # Hiển thị biểu đồ 2D
                        chart_2d_p = None
                        if chart_2d_match and os.path.exists(chart_2d_match.group(1).strip()):
                            chart_2d_p = chart_2d_match.group(1).strip()
                        elif any(k in analysis_query.lower() for k in ["biểu đồ", "đồ thị", "vẽ", "chart"]) and "3d" not in analysis_query.lower() and os.path.exists(os.path.abspath("data/charts/latest_chart.png")):
                            chart_2d_p = os.path.abspath("data/charts/latest_chart.png")

                        if chart_2d_p and os.path.exists(chart_2d_p) and chart_2d_p != chart_3d_p:
                            st.subheader("📈 Biểu đồ dữ liệu 2D:")
                            st.image(chart_2d_p, caption="Biểu đồ được tạo bởi AI Agent", use_container_width=True)
                            with open(chart_2d_p, "rb") as f2:
                                st.download_button("📥 Tải xuống hình ảnh 2D (PNG)", data=f2, file_name="bieu_do_2d.png", mime="image/png")
                    except Exception as exc:
                        st.error(f"⚠️ Lỗi phân tích dữ liệu: {exc}")
            else:
                st.warning("Vui lòng nhập câu hỏi hoặc chọn một trong các gợi ý trên.")


# ------------------------------------------
# TAB 3: TẠO ẢNH AI THEO YÊU CẦU
# ------------------------------------------
with tab_image_gen:
    st.markdown("### 🎨 Tạo Ảnh AI Theo Yêu Cầu Ngôn Ngữ Tự Nhiên")
    st.markdown(
        "Nhập mô tả bất kỳ bằng **tiếng Việt hoặc tiếng Anh** — AI sẽ tạo ra hình ảnh chất lượng cao "
        "dựa trên văn bản của bạn. Hỗ trợ nhiều phong cách: thực tế, anime, 3D, tranh vẽ, nghệ thuật..."
    )

    st.markdown("---")

    # --- Cột trái: Form nhập liệu ---
    col_form, col_preview = st.columns([1, 1], gap="large")

    with col_form:
        st.subheader("✏️ Mô Tả Hình Ảnh Của Bạn")

        # --- Prompt suggestions ---
        st.caption("💡 Gợi ý nhanh — nhấn để điền tự động:")
        suggest_cols = st.columns(2)
        prompt_suggestions = [
            ("🌅 Hoàng hôn trên biển", "A breathtaking sunset over the ocean, golden hour, dramatic clouds, photorealistic, 8K"),
            ("🐉 Rồng châu Á", "Majestic Asian dragon flying through misty mountains, traditional Chinese art style, vibrant colors"),
            ("🏙️ Thành phố tương lai", "Futuristic cyberpunk city at night, neon lights, flying cars, rain-soaked streets, cinematic"),
            ("🌸 Cô gái anime", "Anime girl with long silver hair, sakura blossoms, studio ghibli style, soft pastel colors"),
            ("🦁 Sư tử uy nghi", "Majestic lion portrait, golden mane, African savanna background, National Geographic style"),
            ("🎨 Tranh sơn dầu", "Abstract expressionist oil painting, bold brushstrokes, vibrant colors, museum quality art"),
        ]

        selected_suggestion = None
        for i, (label, prompt_text) in enumerate(prompt_suggestions):
            col_idx = i % 2
            with suggest_cols[col_idx]:
                if st.button(label, key=f"suggest_{i}", use_container_width=True):
                    selected_suggestion = prompt_text

        st.markdown("")

        # Khởi tạo giá trị mặc định cho prompt
        if "image_prompt_value" not in st.session_state:
            st.session_state.image_prompt_value = ""
        if selected_suggestion:
            st.session_state.image_prompt_value = selected_suggestion

        user_prompt = st.text_area(
            "📝 Nhập mô tả ảnh (Tiếng Việt hoặc Tiếng Anh):",
            value=st.session_state.image_prompt_value,
            height=120,
            placeholder=(
                "Ví dụ: 'Một con rồng vàng đang bay lượn trên những đám mây trắng trên bầu trời xanh, "
                "phong cách tranh anime Nhật Bản, màu sắc rực rỡ, chi tiết cao'\n\n"
                "Or in English: 'A majestic golden dragon soaring through white clouds, anime art style, vibrant colors, high detail'"
            ),
            key="image_prompt_input"
        )

        # --- Negative prompt (tùy chọn nâng cao) ---
        with st.expander("🔧 Tùy Chọn Nâng Cao"):
            negative_prompt = st.text_input(
                "❌ Negative Prompt (những gì KHÔNG muốn xuất hiện trong ảnh):",
                placeholder="Ví dụ: blurry, low quality, watermark, text, ugly, deformed",
                key="neg_prompt_input"
            )
            st.markdown("---")
            adv_col1, adv_col2 = st.columns(2)
            with adv_col1:
                img_width = st.select_slider(
                    "↔️ Chiều rộng (px):",
                    options=[512, 640, 768, 800, 896, 1024, 1280, 1536],
                    value=1024,
                    key="img_width_slider"
                )
                enhance_prompt = st.toggle("✨ Tự động tối ưu hóa prompt", value=True, key="enhance_toggle")
            with adv_col2:
                img_height = st.select_slider(
                    "↕️ Chiều cao (px):",
                    options=[512, 640, 768, 800, 896, 1024, 1280, 1536],
                    value=1024,
                    key="img_height_slider"
                )
                seed_input = st.number_input(
                    "🎲 Seed (để tái tạo kết quả, 0 = ngẫu nhiên):",
                    min_value=0,
                    max_value=999999999,
                    value=0,
                    key="seed_input"
                )

        # --- Chọn model AI ---
        st.markdown("")
        MODEL_EMOJI = {
            "flux": "⚡",
            "flux-realism": "📷",
            "flux-anime": "🌸",
            "flux-3d": "🧊",
            "turbo": "🚀",
        }
        model_options = list(AVAILABLE_MODELS.keys())
        final_model = st.selectbox(
            "🤖 Chọn phong cách / model tạo ảnh:",
            options=model_options,
            format_func=lambda m: f"{MODEL_EMOJI.get(m, '🎨')}  {AVAILABLE_MODELS[m]}",
            index=0,
            key="model_selectbox"
        )

        st.markdown("")

        # --- Nút tạo ảnh ---
        generate_btn = st.button(
            "🎨 Tạo Ảnh Ngay!",
            type="primary",
            use_container_width=True,
            key="generate_image_btn"
        )

        # Số lượng ảnh trong lịch sử
        if st.session_state.generated_images:
            st.caption(f"📚 Lịch sử: {len(st.session_state.generated_images)} ảnh đã tạo trong phiên này")
            if st.button("🗑️ Xóa lịch sử ảnh", use_container_width=True, key="clear_history_btn"):
                st.session_state.generated_images = []
                st.rerun()

    # --- Cột phải: Hiển thị ảnh ---
    with col_preview:
        st.subheader("🖼️ Ảnh Được Tạo Ra")

        if generate_btn:
            final_prompt = user_prompt.strip()
            if not final_prompt:
                st.warning("⚠️ Vui lòng nhập mô tả ảnh trước khi nhấn tạo!")
            else:
                neg_prompt = negative_prompt.strip() if ("negative_prompt" in dir() and negative_prompt) else None

                with st.spinner(f"🔮 Đang tạo ảnh với model **{final_model}**... Vui lòng chờ trong giây lát..."):
                    try:
                        seed_val = seed_input if seed_input > 0 else None
                        image_path = generate_ai_art_advanced(
                            prompt=final_prompt,
                            width=img_width,
                            height=img_height,
                            model=final_model,
                            seed=seed_val,
                            enhance=enhance_prompt,
                            negative_prompt=neg_prompt
                        )

                        if image_path and os.path.exists(image_path):
                            # Lưu vào lịch sử
                            st.session_state.generated_images.insert(0, {
                                "path": image_path,
                                "prompt": final_prompt,
                                "model": final_model,
                                "size": f"{img_width}×{img_height}",
                            })

                            st.success("✅ Tạo ảnh thành công!")
                            st.image(
                                image_path,
                                caption=f"🎨 Model: {final_model} | Kích thước: {img_width}×{img_height}px",
                                use_container_width=True
                            )
                            # Nút tải xuống
                            with open(image_path, "rb") as img_file:
                                st.download_button(
                                    label="📥 Tải xuống ảnh (JPG)",
                                    data=img_file,
                                    file_name=f"ai_art_{final_model}.jpg",
                                    mime="image/jpeg",
                                    use_container_width=True
                                )
                        else:
                            st.error(
                                "❌ Không thể tạo ảnh. Có thể do:\n"
                                "- Mạng chậm hoặc timeout (thử lại)\n"
                                "- Prompt chứa nội dung bị từ chối\n"
                                "- Server Pollinations AI tạm thời quá tải"
                            )
                    except Exception as exc:
                        st.error(f"⚠️ Lỗi khi tạo ảnh: {exc}")

        elif not st.session_state.generated_images:
            # Placeholder khi chưa có ảnh
            st.info(
                "👈 Nhập mô tả ảnh ở cột bên trái và nhấn **🎨 Tạo Ảnh Ngay!** để bắt đầu.\n\n"
                "**Mẹo viết prompt hiệu quả:**\n"
                "- Mô tả chi tiết đối tượng chính: *'a white cat with blue eyes'*\n"
                "- Thêm phong cách: *'oil painting', 'photorealistic', 'anime style'*\n"
                "- Chỉ định ánh sáng: *'golden hour lighting', 'studio lighting'*\n"
                "- Thêm chất lượng: *'8K, highly detailed, masterpiece'*"
            )
        else:
            # Hiển thị ảnh gần nhất
            latest = st.session_state.generated_images[0]
            if os.path.exists(latest["path"]):
                st.image(
                    latest["path"],
                    caption=f"🎨 {latest['model']} | {latest['size']}px | {latest['prompt'][:60]}...",
                    use_container_width=True
                )
                with open(latest["path"], "rb") as img_file:
                    st.download_button(
                        label="📥 Tải xuống ảnh mới nhất (JPG)",
                        data=img_file,
                        file_name=f"ai_art_{latest['model']}.jpg",
                        mime="image/jpeg",
                        use_container_width=True
                    )

    # --- Lịch sử ảnh đã tạo ---
    if len(st.session_state.generated_images) > 1:
        st.markdown("---")
        st.subheader("📚 Lịch Sử Ảnh Đã Tạo Trong Phiên Này")
        history_cols = st.columns(min(len(st.session_state.generated_images), 4))
        for i, img_info in enumerate(st.session_state.generated_images[:8]):
            with history_cols[i % 4]:
                if os.path.exists(img_info["path"]):
                    st.image(img_info["path"], use_container_width=True)
                    st.caption(
                        f"**{img_info['model']}** | {img_info['size']}\n"
                        f"_{img_info['prompt'][:50]}..._"
                    )
                    with open(img_info["path"], "rb") as hf:
                        st.download_button(
                            "📥",
                            data=hf,
                            file_name=f"ai_art_{i+1}.jpg",
                            mime="image/jpeg",
                            key=f"dl_hist_{i}"
                        )
