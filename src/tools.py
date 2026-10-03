import os
import polars as pl
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from crewai.tools import tool

@tool("view_csv_schema")
def view_csv_schema(file_path: str) -> str:
    """Hàm này đọc file CSV và trả về danh sách các cột cùng kiểu dữ liệu và một số dòng mẫu."""
    try:
        df = pl.read_csv(file_path, n_rows=5)
        return f"Cấu trúc các cột: {str(df.schema)}\nVí dụ 3 dòng đầu:\n{str(df.head(3))}"
    except Exception as e:
        return f"Lỗi khi đọc file: {str(e)}"

@tool("aggregate_sales")
def aggregate_sales(file_path: str, group_column: str, value_column: str) -> str:
    """Hàm này nhóm dữ liệu theo một cột và tính tổng giá trị của cột khác bằng Polars."""
    try:
        df = pl.read_csv(file_path)
        result = df.group_by(group_column).agg(pl.col(value_column).sum()).sort(value_column, descending=True)
        return str(result.head(10))
    except Exception as e:
        return f"Lỗi tính toán: {str(e)}"

@tool("filter_data")
def filter_data(file_path: str, column_name: str, keyword: str) -> str:
    """Hàm này tìm kiếm các dòng dữ liệu trong file CSV mà cột tương ứng có chứa từ khóa (không phân biệt chữ hoa/thường)."""
    try:
        df = pl.read_csv(file_path)
        filtered = df.filter(pl.col(column_name).cast(pl.Utf8).str.contains(f"(?i){keyword}"))
        if filtered.height == 0:
            return f"Không tìm thấy dòng nào có giá trị '{keyword}' trong cột '{column_name}'."
        return str(filtered.head(15))
    except Exception as e:
        return f"Lỗi khi lọc dữ liệu: {str(e)}"

@tool("calculate_statistics")
def calculate_statistics(file_path: str, target_column: str, agg_func: str = "mean", group_column: str = "") -> str:
    """Hàm tính toán chỉ số thống kê trên cột số liệu bằng Polars:
    - target_column: tên cột số cần tính toán
    - agg_func: 'sum' (tổng), 'mean' (trung bình), 'max' (lớn nhất), 'min' (nhỏ nhất), 'count' (đếm)
    - group_column: tên cột để nhóm lại (tùy chọn, ví dụ theo 'lop', 'phong_ban', 'trieu_dai')
    """
    try:
        df = pl.read_csv(file_path)
        func_map = {
            "sum": pl.col(target_column).sum(),
            "mean": pl.col(target_column).mean(),
            "max": pl.col(target_column).max(),
            "min": pl.col(target_column).min(),
            "count": pl.col(target_column).count(),
        }
        expr = func_map.get(agg_func.lower(), pl.col(target_column).mean())
        if group_column and group_column in df.columns:
            result = df.group_by(group_column).agg(expr.alias(f"{agg_func}_{target_column}")).sort(f"{agg_func}_{target_column}", descending=True)
            return str(result.head(15))
        else:
            val = df.select(expr).to_series()[0]
            return f"Kết quả {agg_func} của cột '{target_column}': {val}"
    except Exception as e:
        return f"Lỗi tính toán: {str(e)}"

@tool("get_top_records")
def get_top_records(file_path: str, sort_column: str, ascending: bool = False, limit: int = 5) -> str:
    """Hàm sắp xếp file dữ liệu theo một cột và lấy ra các dòng đầu (ví dụ: top 5 cao nhất hoặc thấp nhất)."""
    try:
        df = pl.read_csv(file_path)
        result = df.sort(sort_column, descending=not ascending).head(limit)
        return str(result)
    except Exception as e:
        return f"Lỗi sắp xếp: {str(e)}"

@tool("generate_chart")
def generate_chart(file_path: str, chart_type: str, x_column: str, y_column: str, title: str = "") -> str:
    """Tạo biểu đồ trực quan hóa dữ liệu và xuất ra file hình ảnh PNG khi người dùng yêu cầu vẽ hình ảnh, vẽ biểu đồ hoặc đồ thị.
    - file_path: đường dẫn file CSV
    - chart_type: loại biểu đồ, gồm 'bar' (cột), 'line' (đường), 'pie' (tròn)
    - x_column: tên cột cho trục hoành (hoặc nhãn danh mục cho pie chart)
    - y_column: tên cột số cho trục tung (hoặc giá trị cho pie chart)
    - title: tiêu đề hiển thị trên biểu đồ
    """
    try:
        os.makedirs("data/charts", exist_ok=True)
        plt.rcParams['font.sans-serif'] = ['Arial', 'Segoe UI', 'DejaVu Sans', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
        
        df = pl.read_csv(file_path)
        if x_column not in df.columns or y_column not in df.columns:
            return f"Lỗi: Cột '{x_column}' hoặc '{y_column}' không tồn tại trong file. Các cột hiện có: {list(df.columns)}"
        
        # Nhóm dữ liệu nếu có giá trị trùng lặp trên x_column
        if df[x_column].is_duplicated().any():
            plot_df = df.group_by(x_column).agg(pl.col(y_column).sum()).sort(y_column, descending=True).head(12)
        else:
            plot_df = df.sort(y_column, descending=True).head(12)
            
        x_vals = [str(v) for v in plot_df[x_column].to_list()]
        y_vals = [float(v) for v in plot_df[y_column].to_list()]
        
        fig, ax = plt.subplots(figsize=(10, 6), dpi=130)
        
        chart_type_clean = chart_type.lower().strip()
        if chart_type_clean == "pie":
            wedges, texts, autotexts = ax.pie(
                y_vals,
                labels=x_vals,
                autopct="%1.1f%%",
                startangle=140,
                colors=plt.cm.Paired.colors
            )
            for autotext in autotexts:
                autotext.set_fontsize(10)
                autotext.set_weight("bold")
        elif chart_type_clean == "line":
            ax.plot(x_vals, y_vals, marker="o", linewidth=2.5, color="#1e88e5", markersize=8)
            ax.grid(True, linestyle="--", alpha=0.6)
            for i, v in enumerate(y_vals):
                ax.annotate(f"{v:,.0f}" if v >= 1000 else f"{v:.1f}", (x_vals[i], y_vals[i]), textcoords="offset points", xytext=(0, 7), ha='center', fontsize=9, fontweight='bold')
        else: # Mặc định là bar chart
            colors = plt.cm.viridis([i / max(len(x_vals) - 1, 1) for i in range(len(x_vals))])
            bars = ax.bar(x_vals, y_vals, color=colors, edgecolor="black", linewidth=0.5, alpha=0.85)
            ax.grid(axis="y", linestyle="--", alpha=0.5)
            for bar in bars:
                height = bar.get_height()
                label = f"{height:,.0f}" if height >= 1000 else f"{height:.1f}"
                ax.annotate(label,
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 4),
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        chart_title = title if title else f"Biểu đồ {chart_type.upper()}: {y_column} theo {x_column}"
        ax.set_title(chart_title, fontsize=14, fontweight="bold", pad=15)
        if chart_type_clean != "pie":
            ax.set_xlabel(x_column, fontsize=11, fontweight="bold")
            ax.set_ylabel(y_column, fontsize=11, fontweight="bold")
            plt.xticks(rotation=30, ha='right', fontsize=10)
            
        plt.tight_layout()
        
        chart_path = os.path.abspath("data/charts/latest_chart.png")
        fig.savefig(chart_path, bbox_inches="tight")
        plt.close(fig)
        
        return f"Đã vẽ biểu đồ thành công và lưu ảnh tại '{chart_path}'. [CHART:{chart_path}]"
    except Exception as e:
        return f"Lỗi khi tạo biểu đồ: {str(e)}"

@tool("generate_3d_chart")
def generate_3d_chart(file_path: str, x_column: str = "", y_column: str = "", title: str = "") -> str:
    """Tạo hình ảnh biểu đồ không gian 3 chiều 3D (có hình khối nổi, bóng đổ và chiều sâu 3D).
    Đặc biệt sử dụng khi người dùng yêu cầu 'vẽ 3D', 'hình ảnh 3D', 'biểu đồ 3D' hoặc 'mô hình 3D'.
    Nếu người dùng không nói rõ tên cột, công cụ sẽ tự động chọn cột phù hợp nhất.
    - file_path: đường dẫn file CSV
    - x_column: cột phân loại (tùy chọn)
    - y_column: cột số liệu chiều cao 3D (tùy chọn)
    - title: tiêu đề biểu đồ (tùy chọn)
    """
    try:
        os.makedirs("data/charts", exist_ok=True)
        plt.rcParams['font.sans-serif'] = ['Arial', 'Segoe UI', 'DejaVu Sans', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
        
        df = pl.read_csv(file_path)
        
        # Tự động nhận diện cột phù hợp nếu người dùng không rành công nghệ
        if not x_column or x_column not in df.columns:
            str_cols = [c for c, dt in zip(df.columns, df.dtypes) if dt == pl.Utf8 or dt == pl.String]
            x_column = str_cols[0] if str_cols else df.columns[0]
            
        if not y_column or y_column not in df.columns:
            num_cols = [c for c, dt in zip(df.columns, df.dtypes) if dt in [pl.Int64, pl.Float64, pl.Int32, pl.Float32] and c.lower() not in ['id', 'order_id', 'ma_hs']]
            y_column = num_cols[-1] if num_cols else df.columns[1]
            
        # Tổng hợp dữ liệu gọn gàng
        if df[x_column].is_duplicated().any():
            plot_df = df.group_by(x_column).agg(pl.col(y_column).sum()).sort(y_column, descending=True).head(10)
        else:
            plot_df = df.sort(y_column, descending=True).head(10)
            
        x_labels = [str(v) for v in plot_df[x_column].to_list()]
        y_values = [float(v) for v in plot_df[y_column].to_list()]
        n = len(x_labels)
        
        fig = plt.figure(figsize=(11, 7), dpi=140)
        ax = fig.add_subplot(111, projection='3d')
        
        # Tọa độ khối hộp 3D
        xpos = np.arange(n)
        ypos = np.zeros(n)
        zpos = np.zeros(n)
        
        dx = 0.55 * np.ones(n)
        dy = 0.55 * np.ones(n)
        dz = np.array(y_values)
        
        # Bảng màu 3D nổi khối
        colors = plt.cm.plasma(np.linspace(0.15, 0.85, n))
        
        ax.bar3d(xpos, ypos, zpos, dx, dy, dz, color=colors, shade=True, edgecolor='#222222', linewidth=0.5)
        
        # Góc nhìn 3D trực quan
        ax.view_init(elev=28, azim=40)
        
        ax.set_xticks(xpos + 0.28)
        ax.set_xticklabels(x_labels, rotation=25, ha='right', fontsize=9, fontweight='bold')
        ax.set_yticks([]) # Ẩn trục chiều sâu
        
        ax.set_zlabel(y_column, fontsize=10, fontweight='bold')
        chart_title = title if title else f"Biểu Đồ 3D: {y_column} theo {x_column}"
        ax.set_title(chart_title, fontsize=13, fontweight='bold', pad=20)
        
        # Nhãn giá trị trên đỉnh cột 3D
        for i, val in enumerate(y_values):
            label_text = f"{val:,.0f}" if val >= 1000 else f"{val:.1f}"
            ax.text(xpos[i] + 0.28, 0.28, val * 1.02, label_text, ha='center', va='bottom', fontsize=9, fontweight='bold', color='#111111')
            
        chart_path = os.path.abspath("data/charts/latest_3d_chart.png")
        fig.savefig(chart_path, bbox_inches='tight')
        plt.close(fig)
        
        return f"Đã tạo biểu đồ 3D thành công! Tệp hình ảnh lưu tại: '{chart_path}'. [CHART_3D:{chart_path}]"
    except Exception as e:
        return f"Lỗi khi tạo biểu đồ 3D: {str(e)}"

