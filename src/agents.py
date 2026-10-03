import os
import sys
from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from crewai import Agent, Task, Crew, Process, LLM
from src.tools import (
    view_csv_schema,
    aggregate_sales,
    filter_data,
    calculate_statistics,
    get_top_records,
    generate_chart,
    generate_3d_chart
)

load_dotenv()

def get_llm():
    """Tự động nhận diện API Key được cung cấp để chọn LLM phù hợp."""
    load_dotenv(override=True)
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if groq_key:
        return LLM(
            model="openai/openai/gpt-oss-120b",
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_key
        )
    elif gemini_key:
        return LLM(model="gemini/gemini-1.5-flash", api_key=gemini_key)
    elif openai_key:
        model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
        return LLM(model=model_name, api_key=openai_key)
    else:
        raise ValueError(
            "Chưa cấu hình API Key! Vui lòng điền GEMINI_API_KEY (hoàn toàn miễn phí tại https://aistudio.google.com/app/apikey) "
            "hoặc GROQ_API_KEY / OPENAI_API_KEY vào file .env"
        )

def create_analysis_crew(file_path: str, user_question: str):
    llm = get_llm()
    
    # Khởi tạo Agent phân tích dữ liệu
    agent_kwargs = {
        "role": "Chuyên viên Phân tích Dữ liệu Polars",
        "goal": "Đọc cấu trúc file dữ liệu và đưa ra các câu lệnh tính toán chính xác.",
        "backstory": "Bạn là một chuyên gia về Polars, hiểu rõ cách tối ưu hóa truy vấn dữ liệu lớn.",
        "verbose": True,
        "tools": [
            view_csv_schema,
            aggregate_sales,
            filter_data,
            calculate_statistics,
            get_top_records,
            generate_chart,
            generate_3d_chart
        ],
    }
    if llm:
        agent_kwargs["llm"] = llm
        
    data_analyst = Agent(**agent_kwargs)
    
    # Định nghĩa nhiệm vụ
    analysis_task = Task(
        description=(
            f"Hãy phân tích file tại '{file_path}' và trả lời câu hỏi: '{user_question}' dựa trên các công cụ sẵn có. "
            "Nếu câu hỏi yêu cầu vẽ biểu đồ 3D, tạo hình ảnh 3D, hoặc mô hình 3D, hãy ưu tiên dùng công cụ generate_3d_chart. "
            "Nếu câu hỏi yêu cầu vẽ biểu đồ thông thường (cột, tròn, đường), hãy dùng công cụ generate_chart."
        ),
        expected_output="Bảng kết quả tính toán chi tiết, kết luận ngắn gọn bằng tiếng Việt và thông báo kèm đường dẫn file biểu đồ nếu có.",
        agent=data_analyst
    )
    
    # Kết hợp thành tổ đội
    crew = Crew(
        agents=[data_analyst],
        tasks=[analysis_task],
        process=Process.sequential
    )
    return crew

