import os
import sys
import re
import requests
import streamlit as st

# Đảm bảo import được module từ thư mục src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.chat_service import (
    EXPERT_PERSONAS,
    stream_chat_response,
    read_local_file
)
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
    st.subheader("📁 Nạp Tệp/Tài Liệu (Tùy chọn)")
    st.caption("AI không bị bó buộc vào thư mục nào. Bạn có thể tải file lên hoặc nhập đường dẫn file bất kỳ trên máy tính.")

    attached_text = None
    # 1. Tải file từ máy tính
    uploaded_any_file = st.file_uploader(
        "Tải lên tệp (code, text, csv, json, md...):",
        type=["py", "js", "ts", "html", "css", "json", "csv", "txt", "md", "sql", "yaml", "env", "sh"]
    )
    if uploaded_any_file is not None:
        try:
            raw_bytes = uploaded_any_file.read()
            decoded_text = raw_bytes.decode("utf-8", errors="replace")
            attached_text = f"=== TỆP TẢI LÊN: {uploaded_any_file.name} ===\n{decoded_text[:12000]}\n=== HẾT TỆP ==="
            st.success(f"📎 Đã nhận tệp: `{uploaded_any_file.name}` ({len(decoded_text)} ký tự)")
        except Exception as err:
            st.error(f"Lỗi đọc file: {err}")

    # 2. Hoặc nhập đường dẫn trực tiếp trên máy tính
    manual_file_path = st.text_input(
        "Hoặc nhập đường dẫn file trên máy tính:",
        placeholder="Ví dụ: C:\\Users\\Admin\\project\\main.py"
    )
    if manual_file_path:
        local_content = read_local_file(manual_file_path)
        if not local_content.startswith("[Lỗi"):
            attached_text = local_content
            st.success("✅ Đã nạp nội dung từ đường dẫn máy tính!")
        else:
            st.warning(local_content)

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
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"])

    # Gợi ý nhanh nếu đoạn chat còn mới
    if len(st.session_state.chat_messages) <= 1:
        st.write("💡 **Gợi ý yêu cầu nhanh:**")
        col_s1, col_s2, col_s3 = st.columns(3)
        prompt_preset = None
        with col_s1:
            if st.button("🛠️ Viết ứng dụng CRUD bằng Python"):
                prompt_preset = "Hãy hướng dẫn và viết code mẫu xây dựng một ứng dụng REST API CRUD hoàn chỉnh bằng FastAPI và SQLite, tuân thủ Clean Architecture."
        with col_s2:
            if st.button("⚡ Tối ưu thuật toán & Cấu trúc dữ liệu"):
                prompt_preset = "Giải thích sự khác biệt giữa mảng tĩnh và danh sách liên kết, kèm bài toán thực tế khi nào nên chọn cái nào."
        with col_s3:
            if st.button("📊 Phân tích cách xử lý dữ liệu lớn"):
                prompt_preset = "So sánh hiệu năng giữa Polars và Pandas khi xử lý tập dữ liệu lớn hàng chục gigabyte."

        if prompt_preset:
            # Thêm prompt vào phiên chat
            st.session_state.chat_messages.append({"role": "user", "content": prompt_preset})
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(prompt_preset)

            with st.chat_message("assistant", avatar="🤖"):
                chat_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages]
                response_stream = stream_chat_response(
                    messages=chat_history,
                    persona_key=selected_persona_key,
                    attached_content=attached_text
                )
                full_reply = st.write_stream(response_stream)
                st.session_state.chat_messages.append({"role": "assistant", "content": full_reply})
            st.rerun()

    # Khung nhập chat trực tiếp
    user_input = st.chat_input("Nhập câu hỏi, yêu cầu viết code hoặc chủ đề thảo luận của bạn...")
    if user_input:
        # Thêm tin nhắn người dùng
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(user_input)

        # AI trả lời với hiệu ứng Streaming thời gian thực
        with st.chat_message("assistant", avatar="🤖"):
            chat_history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages]
            response_stream = stream_chat_response(
                messages=chat_history,
                persona_key=selected_persona_key,
                attached_content=attached_text
            )
            full_reply = st.write_stream(response_stream)
            st.session_state.chat_messages.append({"role": "assistant", "content": full_reply})


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
                # Ghép negative prompt nếu có
                full_prompt = final_prompt
                if "negative_prompt" in dir() and negative_prompt:
                    full_prompt = final_prompt  # Pollinations xử lý negative riêng

                with st.spinner(f"🔮 Đang tạo ảnh với model **{final_model}**... Vui lòng chờ trong giây lát..."):
                    try:
                        seed_val = seed_input if seed_input > 0 else None
                        image_path = generate_ai_art_advanced(
                            prompt=full_prompt,
                            width=img_width,
                            height=img_height,
                            model=final_model,
                            seed=seed_val,
                            enhance=enhance_prompt
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
