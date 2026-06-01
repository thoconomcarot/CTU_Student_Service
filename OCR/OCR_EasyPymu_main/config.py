"""
config.py
Cấu hình chung cho pipeline OCR EasyOCR + PyMuPDF.

File này chỉ giữ các hằng số, đường dẫn và danh sách định dạng hỗ trợ.
Không đặt logic OCR / xử lý layout ở đây để code dễ bảo trì.
"""

from pathlib import Path

# Luôn lấy đường dẫn theo vị trí file main.py/config.py, không phụ thuộc terminal đang đứng ở đâu.
# Nếu folder code nằm trực tiếp trong project như: CTU_Student_Service/OCR_EasyPymu_modular
# thì PROJECT_ROOT sẽ là CTU_Student_Service để dùng chung input/output như bản gốc.
SCRIPT_DIR = Path(__file__).resolve().parent

if SCRIPT_DIR.name.lower() in {"ocr", "ocr_easypymu_modular", "ocr_easypymu_main"}:
    PROJECT_ROOT = SCRIPT_DIR.parent
else:
    PROJECT_ROOT = SCRIPT_DIR

INPUT_FOLDER = PROJECT_ROOT / "input"
OUTPUT_FOLDER = PROJECT_ROOT / "output"
IMAGE_TEMP_FOLDER = OUTPUT_FOLDER / "temp_images"

SUPPORTED_PDF = {".pdf"}
SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}

# Ngôn ngữ OCR: tiếng Việt + tiếng Anh.
OCR_LANGS = ["vi", "en"]
USE_GPU = False

# Nếu trang có số ký tự ít hơn mức này thì xem như cần OCR.
MIN_TEXT_LENGTH = 30

# DPI khi chuyển PDF scan sang ảnh; 200 nhẹ hơn 300 cho máy yếu.
RENDER_DPI = 200


def ensure_output_dirs() -> None:
    """Tạo thư mục output và temp_images nếu chưa tồn tại."""

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    IMAGE_TEMP_FOLDER.mkdir(parents=True, exist_ok=True)
