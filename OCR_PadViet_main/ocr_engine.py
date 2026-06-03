"""
ocr_dong_co.py
Động cơ OCR: PaddleOCR detection/recognition + VietOCR recognition.

Tái sử dụng các phần tốt từ source cũ:
- Lazy-load PaddleOCR/VietOCR để không khởi tạo nhiều lần.
- PaddleOCR detect box, VietOCR nhận dạng crop cho tiếng Việt.
- Fallback PaddleOCR recognition nếu dòng nghi có @, URL, Email, ký tự đặc biệt.
- Hỗ trợ fallback nhiều ngôn ngữ PaddleOCR: vi, latin, en.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import re
import unicodedata


VIETNAMESE_MARK_RE = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễ"
    r"ìíịỉĩòóọỏõôồốộổỗơờớợởỡ"
    r"ùúụủũưừứựửữỳýỵỷỹđ"
    r"ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄ"
    r"ÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ"
    r"ÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]"
)

WORD_RE = re.compile(r"[A-Za-zÀ-ỹĐđ0-9_]+", re.UNICODE)
LETTER_RE = re.compile(r"[A-Za-zÀ-ỹĐđ]", re.UNICODE)

# Từ vựng tiếng Việt phổ biến trong văn bản hành chính/học vụ.
# Đây không phải rule riêng cho một file; chỉ dùng để nhận biết ngữ cảnh là tài liệu tiếng Việt.
VI_COMMON_WORDS = {
    "bo", "giao", "duc", "dao", "tao", "truong", "dai", "hoc", "can", "tho",
    "cong", "hoa", "xa", "hoi", "chu", "nghia", "viet", "nam", "doc", "lap", "tu", "do", "hanh", "phuc",
    "quyet", "dinh", "quy", "che", "can", "cu", "luat", "nghi", "so", "ngay", "thang", "nam",
    "dieu", "khoan", "diem", "muc", "chuong", "phu", "luc", "ban", "hanh", "kem", "theo",
    "hieu", "truong", "phong", "khoa", "vien", "trung", "tam", "don", "vi", "sinh", "nguoi",
    "hoc", "vien", "cong", "tac", "suc", "khoe", "tam", "ly", "noi", "dung", "thuc", "hien",
    "duoc", "voi", "ve", "va", "cua", "cho", "trong", "ngoai", "phoi", "hop", "bao", "cao",
    "trach", "nhiem", "quan", "ly", "dao", "tao", "lien", "quan", "thong", "tin", "thoi", "gian",
}


def bo_dau_de_danh_gia(text: str) -> str:
    """Bỏ dấu tiếng Việt để so sánh từ vựng khi đánh giá chất lượng text layer."""

    text = str(text).replace("Đ", "D").replace("đ", "d")
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def danh_gia_chat_luong_text_layer(text: str) -> dict[str, object]:
    """
    Đánh giá text layer lấy bằng PyMuPDF có đáng tin không.

    Hàm này dùng các tiêu chí tổng quát, không phụ thuộc vào một file cụ thể:
    - Tỷ lệ ký tự/ký hiệu lạ trong từ.
    - Từ có số hoặc ký hiệu chen giữa chữ, ví dụ OCR lỗi dạng d6i, xu 1y, h9c.
    - Dấu hiệu mojibake/encoding hỏng, ví dụ ký tự �, Ã, Ä, Æ xuất hiện bất thường.
    - Tỷ lệ dấu tiếng Việt quá thấp trong khi ngữ cảnh giống văn bản tiếng Việt.
    - Từ in hoa dính liền bất thường do OCR text layer cũ.

    Trả về dict để main.py có thể in lý do debug nếu cần.
    """

    raw = str(text or "")
    cleaned = raw.strip()
    if len(cleaned) < 30:
        return {
            "is_bad": False,
            "score": 0,
            "reason": "text_layer_too_short_or_empty",
            "length": len(cleaned),
        }

    sample = cleaned[:6000]
    sample_no_accents = bo_dau_de_danh_gia(sample).lower()
    tokens = WORD_RE.findall(sample)
    tokens_no_accents = [bo_dau_de_danh_gia(token).lower() for token in tokens]
    token_count = len(tokens)
    letters = LETTER_RE.findall(sample)
    letter_count = len(letters)

    mark_count = len(VIETNAMESE_MARK_RE.findall(sample))
    mark_ratio = _safe_ratio(mark_count, letter_count)

    # Ký tự rất hay xuất hiện khi text layer OCR cũ hoặc font cmap bị lỗi.
    # Không dùng danh sách lỗi theo từng file; chỉ xét nhóm ký hiệu bất thường trong chữ.
    weird_char_count = len(re.findall(r"[~\\{}\[\]<>£^�]", sample))
    weird_char_ratio = _safe_ratio(weird_char_count, max(len(sample), 1))

    # Từ có số/ký hiệu chen giữa chữ: d6i, h9c, xu 1y, QyD, Dl)C...
    digit_inside_word = re.findall(r"(?i)\b[a-zà-ỹđ]+\d+[a-zà-ỹđ]+\b|\b[a-zà-ỹđ]+\s+\d+[a-zà-ỹđ]+\b", sample)
    symbol_inside_word = re.findall(r"(?i)\b[a-zà-ỹđ]*[~\\{}\[\]<>£^\)\(]+[a-zà-ỹđ]+\b|\b[a-zà-ỹđ]+[~\\{}\[\]<>£^\)\(]+[a-zà-ỹđ]*\b", sample)
    suspicious_token_count = len(digit_inside_word) + len(symbol_inside_word)
    suspicious_token_ratio = _safe_ratio(suspicious_token_count, max(token_count, 1))

    # Mojibake/encoding hỏng. Các ký tự này có thể xuất hiện riêng lẻ trong tiếng Việt,
    # nên chỉ tăng điểm khi xuất hiện thành cụm hoặc có ký tự thay thế �.
    mojibake_count = len(re.findall(r"�|Ã.|Ä.|Æ.|Ð.|\uFFFD", sample))

    # Từ viết hoa dính liền dài bất thường: CONGHOAXAHOI, TRUONGDAIHOC...
    glued_upper_words = re.findall(r"\b[A-ZĐ]{10,}\b", sample)
    glued_upper_ratio = _safe_ratio(len(glued_upper_words), max(token_count, 1))

    # Nhận biết ngữ cảnh tiếng Việt/hành chính bằng từ đã bỏ dấu.
    common_hits = sum(1 for token in tokens_no_accents if token in VI_COMMON_WORDS)
    common_ratio = _safe_ratio(common_hits, max(token_count, 1))

    # Từ quá dài hoặc có dạng khó tin thường tăng khi OCR dính chữ.
    long_token_count = sum(1 for token in tokens if len(token) >= 22)
    long_token_ratio = _safe_ratio(long_token_count, max(token_count, 1))

    score = 0
    reasons: list[str] = []

    if mojibake_count >= 2:
        score += 5
        reasons.append("mojibake_or_encoding_noise")

    if suspicious_token_ratio >= 0.08:
        score += 4
        reasons.append("many_tokens_with_digit_or_symbol_inside")
    elif suspicious_token_ratio >= 0.035:
        score += 2
        reasons.append("some_tokens_with_digit_or_symbol_inside")

    if weird_char_ratio >= 0.012:
        score += 3
        reasons.append("high_weird_character_ratio")
    elif weird_char_count >= 5:
        score += 1
        reasons.append("weird_characters_present")

    if glued_upper_ratio >= 0.035 or len(glued_upper_words) >= 4:
        score += 2
        reasons.append("glued_uppercase_words")

    if long_token_ratio >= 0.04:
        score += 2
        reasons.append("many_unusually_long_tokens")

    # Với văn bản tiếng Việt, nếu nhận ra nhiều từ ngữ cảnh nhưng gần như mất hết dấu
    # thì rất có khả năng text layer cũ không đáng tin.
    if common_ratio >= 0.16 and mark_ratio < 0.018 and letter_count >= 120:
        score += 4
        reasons.append("vietnamese_context_but_almost_no_diacritics")
    elif common_ratio >= 0.12 and mark_ratio < 0.035 and suspicious_token_ratio >= 0.02:
        score += 2
        reasons.append("vietnamese_context_low_diacritics_with_noise")

    # Nếu text layer vừa có dấu tiếng Việt tốt, vừa ít noise thì giữ PyMuPDF.
    looks_good_vietnamese = common_ratio >= 0.10 and mark_ratio >= 0.055 and suspicious_token_ratio < 0.025 and weird_char_count <= 3
    if looks_good_vietnamese:
        score = max(0, score - 3)
        reasons.append("looks_like_valid_vietnamese_text")

    is_bad = score >= 4
    return {
        "is_bad": is_bad,
        "score": score,
        "reason": ",".join(reasons) if reasons else "ok",
        "length": len(cleaned),
        "token_count": token_count,
        "mark_ratio": round(mark_ratio, 4),
        "common_ratio": round(common_ratio, 4),
        "weird_char_count": weird_char_count,
        "weird_char_ratio": round(weird_char_ratio, 4),
        "suspicious_token_count": suspicious_token_count,
        "suspicious_token_ratio": round(suspicious_token_ratio, 4),
        "mojibake_count": mojibake_count,
        "glued_upper_words": len(glued_upper_words),
        "long_token_count": long_token_count,
    }


def is_bad_pdf_text_layer(text: str) -> bool:
    """Giữ lại tên hàm cũ để các chỗ import cũ không bị lỗi."""

    return bool(danh_gia_chat_luong_text_layer(text).get("is_bad"))


# Set env trước khi import paddle để ổn định CPU Windows.
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_enable_mkldnn", "0")
os.environ.setdefault("FLAGS_use_onednn", "0")
os.environ.setdefault("FLAGS_enable_onednn", "0")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

try:
    from paddleocr import PaddleOCR
except Exception as exc:  # pragma: no cover
    raise ImportError(
        "Không import được PaddleOCR. Cài bằng: pip install paddleocr==2.9.1 paddlepaddle"
    ) from exc

from config import CauHinhOCR, CAU_HINH_MAC_DINH, lam_sach_dong, lam_sach_text, ten_file_an_toan
from common_fix import hau_xu_ly_loi_chung, nghi_ngo_co_ky_tu_dac_biet
from image_preprocess import (
    crop_box_xoay,
    cv_sang_pil,
    doc_anh_unicode,
    ghi_anh_unicode,
    tao_bien_the_anh_ocr,
    xoa_anh_bien_the,
)

_OCR_ENGINES: dict[str, PaddleOCR] = {}
_VIETOCR_ENGINE: Any | None = None


def ap_dung_moi_truong_paddle(cau_hinh: CauHinhOCR = CAU_HINH_MAC_DINH) -> None:
    """Áp dụng cấu hình runtime cho PaddleOCR, nhất là tắt MKLDNN/OneDNN trên CPU yếu."""

    if cau_hinh.bat_mkldnn:
        os.environ["FLAGS_use_mkldnn"] = "1"
        os.environ["FLAGS_enable_mkldnn"] = "1"
        os.environ["FLAGS_use_onednn"] = "1"
        os.environ["FLAGS_enable_onednn"] = "1"
    else:
        os.environ["FLAGS_use_mkldnn"] = "0"
        os.environ["FLAGS_enable_mkldnn"] = "0"
        os.environ["FLAGS_use_onednn"] = "0"
        os.environ["FLAGS_enable_onednn"] = "0"

    os.environ["OMP_NUM_THREADS"] = str(max(1, int(cau_hinh.so_luong_cpu_threads)))
    os.environ["MKL_NUM_THREADS"] = str(max(1, int(cau_hinh.so_luong_cpu_threads)))


def lay_paddle_ocr(cau_hinh: CauHinhOCR = CAU_HINH_MAC_DINH, lang: str | None = None) -> PaddleOCR:
    """Khởi tạo PaddleOCR lazy-load và cache theo ngôn ngữ."""

    ap_dung_moi_truong_paddle(cau_hinh)
    selected_lang = str(lang or cau_hinh.ngon_ngu_ocr or "vi").strip() or "vi"

    if selected_lang not in _OCR_ENGINES:
        print(f"[INIT] PaddleOCR lang={selected_lang}, gpu={cau_hinh.dung_gpu}")
        base_kwargs = dict(
            use_angle_cls=True,
            lang=selected_lang,
            use_gpu=cau_hinh.dung_gpu,
            show_log=False,
        )
        stable_kwargs = dict(
            enable_mkldnn=cau_hinh.bat_mkldnn,
            cpu_threads=cau_hinh.so_luong_cpu_threads,
            drop_score=cau_hinh.ocr_drop_score,
            det_db_thresh=cau_hinh.det_db_thresh,
            det_db_box_thresh=cau_hinh.det_db_box_thresh,
            det_db_unclip_ratio=cau_hinh.det_db_unclip_ratio,
            use_dilation=True,
            det_limit_side_len=2048,
        )
        try:
            engine = PaddleOCR(**base_kwargs, **stable_kwargs)
        except TypeError:
            try:
                engine = PaddleOCR(
                    **base_kwargs,
                    enable_mkldnn=cau_hinh.bat_mkldnn,
                    cpu_threads=cau_hinh.so_luong_cpu_threads,
                    drop_score=cau_hinh.ocr_drop_score,
                )
            except TypeError:
                engine = PaddleOCR(**base_kwargs)
        _OCR_ENGINES[selected_lang] = engine

    return _OCR_ENGINES[selected_lang]


def lay_vietocr(cau_hinh: CauHinhOCR = CAU_HINH_MAC_DINH) -> Any | None:
    """Khởi tạo VietOCR lazy-load; lỗi thì trả None để fallback PaddleOCR."""

    global _VIETOCR_ENGINE
    if not cau_hinh.dung_vietocr:
        return None
    if _VIETOCR_ENGINE is not None:
        return _VIETOCR_ENGINE

    try:
        from vietocr.tool.config import Cfg
        from vietocr.tool.predictor import Predictor
    except Exception as exc:
        print(f"[WARN] Chưa cài VietOCR hoặc import lỗi: {exc}")
        print("       Cài thêm: pip install vietocr torch torchvision pillow")
        return None

    try:
        model_name = str(cau_hinh.vietocr_model or "vgg_transformer").strip() or "vgg_transformer"
        print(f"[INIT] VietOCR model={model_name}, gpu={cau_hinh.dung_gpu}")
        config = Cfg.load_config_from_name(model_name)
        config["device"] = "cuda:0" if cau_hinh.dung_gpu else "cpu"
        if cau_hinh.vietocr_weights:
            config["weights"] = cau_hinh.vietocr_weights
        _VIETOCR_ENGINE = Predictor(config)
        return _VIETOCR_ENGINE
    except Exception as exc:
        print(f"[WARN] Không khởi tạo được VietOCR, fallback PaddleOCR: {exc}")
        return None


def la_so(value: Any) -> bool:
    """Kiểm tra một giá trị có ép sang float được không."""

    try:
        float(value)
        return True
    except Exception:
        return False


def giong_diem(obj: Any) -> bool:
    """Kiểm tra object có giống một điểm [x, y] hay không."""

    return isinstance(obj, (list, tuple)) and len(obj) >= 2 and la_so(obj[0]) and la_so(obj[1])


def giong_box(obj: Any) -> bool:
    """Kiểm tra object có giống box 4 điểm của PaddleOCR hay không."""

    return isinstance(obj, (list, tuple)) and len(obj) >= 4 and all(giong_diem(p) for p in obj[:4])


def duyet_box_paddle(result: Any):
    """Duyệt kết quả PaddleOCR detection ở nhiều format khác nhau và yield box."""

    if result is None:
        return
    queue = [result]
    seen_ids: set[int] = set()
    while queue:
        obj = queue.pop(0)
        if obj is None:
            continue
        obj_id = id(obj)
        if obj_id in seen_ids:
            continue
        seen_ids.add(obj_id)

        if giong_box(obj):
            yield [[float(p[0]), float(p[1])] for p in obj[:4]]
            continue
        if isinstance(obj, dict):
            for value in obj.values():
                if isinstance(value, (list, tuple, dict)):
                    queue.append(value)
            continue
        if isinstance(obj, (list, tuple)):
            for item in obj:
                if isinstance(item, (list, tuple, dict)):
                    queue.append(item)


def thong_so_box(box: list[list[float]]) -> tuple[float, float, float, float, float, float]:
    """Tính left/top/right/bottom/center_y/height của box OCR."""

    xs = [float(p[0]) for p in box]
    ys = [float(p[1]) for p in box]
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    height = max(1.0, bottom - top)
    center_y = (top + bottom) / 2.0
    return left, top, right, bottom, center_y, height


def sap_xep_box_theo_thu_tu_doc(boxes: list[list[list[float]]]) -> list[list[list[float]]]:
    """Sắp xếp box theo thứ tự đọc tự nhiên: trên xuống, trái sang phải."""

    if not boxes:
        return []
    heights = sorted(thong_so_box(box)[5] for box in boxes)
    median_height = heights[len(heights) // 2]
    line_threshold = max(8.0, median_height * 0.65)

    items = []
    for box in boxes:
        left, top, _, _, center_y, _ = thong_so_box(box)
        items.append({"box": box, "left": left, "top": top, "center_y": center_y})

    items.sort(key=lambda item: (item["top"], item["left"]))
    lines: list[list[dict[str, Any]]] = []
    for item in items:
        placed = False
        for line in lines:
            line_center = sum(x["center_y"] for x in line) / len(line)
            if abs(item["center_y"] - line_center) <= line_threshold:
                line.append(item)
                placed = True
                break
        if not placed:
            lines.append([item])

    sorted_boxes: list[list[list[float]]] = []
    for line in lines:
        line.sort(key=lambda item: item["left"])
        sorted_boxes.extend([item["box"] for item in line])
    return sorted_boxes


def loai_trung_box(boxes: list[list[list[float]]]) -> list[list[list[float]]]:
    """Loại box trùng nhau nhưng giữ thứ tự đầu tiên."""

    deduped: list[list[list[float]]] = []
    seen: set[tuple[int, ...]] = set()
    for box in boxes:
        flat: list[int] = []
        for p in box:
            flat.extend([round(float(p[0])), round(float(p[1]))])
        key = tuple(flat)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(box)
    return deduped


def chay_detect_paddle(engine: PaddleOCR, image_input: Any) -> list[list[list[float]]]:
    """Chạy PaddleOCR detection only và trả danh sách box đã sắp xếp."""

    try:
        result = engine.ocr(image_input, det=True, rec=False, cls=False)
    except TypeError:
        try:
            result = engine.ocr(image_input, rec=False)
        except TypeError:
            result = engine.ocr(image_input)
    boxes = loai_trung_box(list(duyet_box_paddle(result)))
    return sap_xep_box_theo_thu_tu_doc(boxes)


def nhan_dang_crop_vietocr(vietocr_engine: Any, crop_image) -> str:
    """Nhận dạng một crop bằng VietOCR."""

    pil_image = cv_sang_pil(crop_image)
    if pil_image is None or vietocr_engine is None:
        return ""
    try:
        text = vietocr_engine.predict(pil_image)
    except TypeError:
        text = vietocr_engine.predict(pil_image, return_prob=False)
    return lam_sach_dong(text)


def rut_text_tu_dong_paddle(obj: Any) -> str | None:
    """Rút text từ một dòng kết quả PaddleOCR phổ biến: [box, (text, score)]."""

    if isinstance(obj, dict):
        for key in ("text", "transcription"):
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return None

    if isinstance(obj, (list, tuple)) and len(obj) >= 2:
        candidate = obj[1]
        if isinstance(candidate, (list, tuple)) and candidate:
            if isinstance(candidate[0], str) and candidate[0].strip():
                return candidate[0]
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


def duyet_text_paddle(result: Any):
    """Duyệt kết quả PaddleOCR ở nhiều format khác nhau và yield text."""

    if result is None:
        return
    queue = [result]
    seen_ids: set[int] = set()
    while queue:
        obj = queue.pop(0)
        if obj is None:
            continue
        obj_id = id(obj)
        if obj_id in seen_ids:
            continue
        seen_ids.add(obj_id)

        direct_text = rut_text_tu_dong_paddle(obj)
        if direct_text:
            yield direct_text
            continue
        if isinstance(obj, str):
            if obj.strip():
                yield obj
            continue
        if isinstance(obj, dict):
            for value in obj.values():
                if isinstance(value, (list, tuple, dict, str)):
                    queue.append(value)
            continue
        if isinstance(obj, (list, tuple)):
            for item in obj:
                if isinstance(item, (list, tuple, dict, str)):
                    queue.append(item)


def nhan_dang_crop_paddle(engine: PaddleOCR, crop_image) -> str:
    """Nhận dạng lại một crop bằng PaddleOCR recognition, dùng cho dòng có ký tự đặc biệt."""

    try:
        result = engine.ocr(crop_image, det=False, rec=True, cls=False)
    except TypeError:
        try:
            result = engine.ocr(crop_image, det=False, rec=True)
        except TypeError:
            result = engine.ocr(crop_image)
    texts = [lam_sach_dong(t) for t in duyet_text_paddle(result) if lam_sach_dong(t)]
    return lam_sach_dong(" ".join(texts))


def chon_text_tot_hon(viet_text: str, paddle_text: str) -> str:
    """Chọn kết quả tốt hơn giữa VietOCR và PaddleOCR cho dòng nghi có ký tự đặc biệt."""

    viet_text = hau_xu_ly_loi_chung(viet_text)
    paddle_text = hau_xu_ly_loi_chung(paddle_text)
    if not paddle_text:
        return viet_text
    if "@" in paddle_text and "@" not in viet_text:
        return paddle_text
    if paddle_text.count("?") < viet_text.count("?"):
        return paddle_text
    if len(paddle_text) > len(viet_text) + 5 and "?" not in paddle_text:
        return paddle_text
    return viet_text


def nhan_dang_crop(vietocr_engine: Any, paddle_engine: PaddleOCR, crop_image, cau_hinh: CauHinhOCR) -> str:
    """Nhận dạng crop bằng VietOCR và fallback PaddleOCR nếu nghi lỗi ký tự đặc biệt."""

    if vietocr_engine is not None:
        viet_text = nhan_dang_crop_vietocr(vietocr_engine, crop_image)
    else:
        viet_text = ""

    if not viet_text:
        return hau_xu_ly_loi_chung(nhan_dang_crop_paddle(paddle_engine, crop_image))

    viet_text = hau_xu_ly_loi_chung(viet_text)
    if not cau_hinh.fallback_ky_tu_dac_biet:
        return viet_text
    if not nghi_ngo_co_ky_tu_dac_biet(viet_text):
        return viet_text

    try:
        paddle_text = nhan_dang_crop_paddle(paddle_engine, crop_image)
    except Exception:
        paddle_text = ""
    return chon_text_tot_hon(viet_text, paddle_text)


def luu_crop_debug(crop_image, image_path: str, index: int, cau_hinh: CauHinhOCR) -> None:
    """Lưu crop chữ để debug nếu bật `luu_crop_vietocr`."""

    if not cau_hinh.luu_crop_vietocr:
        return
    try:
        crop_dir = os.path.join(cau_hinh.thu_muc_output, "vietocr_crops")
        os.makedirs(crop_dir, exist_ok=True)
        stem = ten_file_an_toan(Path(image_path).stem)
        out_path = os.path.join(crop_dir, f"{stem}_crop_{index:04d}.png")
        ghi_anh_unicode(out_path, crop_image)
    except Exception:
        pass


def ocr_anh_bang_paddle_vietocr(image_path: str, cau_hinh: CauHinhOCR = CAU_HINH_MAC_DINH) -> str:
    """OCR ảnh bằng PaddleOCR detect box + VietOCR recognize crop."""

    vietocr_engine = lay_vietocr(cau_hinh)
    image_variants = tao_bien_the_anh_ocr(image_path, cau_hinh=cau_hinh)

    candidate_langs: list[str] = []
    for lang in [cau_hinh.ngon_ngu_ocr, "vi", "latin", "en"]:
        lang = str(lang or "").strip()
        if lang and lang not in candidate_langs:
            candidate_langs.append(lang)

    last_error = ""
    try:
        for lang in candidate_langs:
            try:
                paddle_engine = lay_paddle_ocr(cau_hinh, lang=lang)
            except Exception as exc:
                last_error = str(exc)
                print(f"[WARN] Không khởi tạo được PaddleOCR lang={lang}: {exc}")
                continue

            for variant_index, variant_path in enumerate(image_variants, start=1):
                image = doc_anh_unicode(variant_path)
                if image is None:
                    continue
                try:
                    boxes = chay_detect_paddle(paddle_engine, variant_path)
                except Exception as exc:
                    last_error = str(exc)
                    print(f"[WARN] PaddleOCR detection lỗi với {variant_path}, lang={lang}: {exc}")
                    continue
                if not boxes:
                    continue

                texts: list[str] = []
                for box_index, box in enumerate(boxes, start=1):
                    crop = crop_box_xoay(image, box, padding=cau_hinh.padding_crop)
                    if crop is None:
                        continue
                    luu_crop_debug(crop, variant_path, box_index, cau_hinh)
                    text = nhan_dang_crop(vietocr_engine, paddle_engine, crop, cau_hinh)
                    if text:
                        texts.append(text)

                if texts:
                    if variant_index > 1:
                        print(f"[INFO] OCR thành công bằng ảnh biến thể {variant_index}: {variant_path}")
                    if lang != cau_hinh.ngon_ngu_ocr:
                        print(f"[INFO] OCR thành công bằng fallback lang={lang}")
                    return lam_sach_text("\n".join(texts))
    finally:
        xoa_anh_bien_the(image_path, image_variants, cau_hinh)

    if last_error:
        print(f"[WARN] OCR không đọc được text từ {image_path}. Lỗi cuối: {last_error}")
    return ""


def ocr_anh_paddle_thuan(image_path: str, cau_hinh: CauHinhOCR = CAU_HINH_MAC_DINH) -> str:
    """OCR ảnh bằng PaddleOCR thuần, dùng làm fallback nếu VietOCR không chạy."""

    image_variants = tao_bien_the_anh_ocr(image_path, cau_hinh=cau_hinh)
    candidate_langs: list[str] = []
    for lang in [cau_hinh.ngon_ngu_ocr, "latin", "en", "vi"]:
        lang = str(lang or "").strip()
        if lang and lang not in candidate_langs:
            candidate_langs.append(lang)

    try:
        for lang in candidate_langs:
            try:
                engine = lay_paddle_ocr(cau_hinh, lang=lang)
            except Exception as exc:
                print(f"[WARN] Không khởi tạo được PaddleOCR lang={lang}: {exc}")
                continue
            for variant_path in image_variants:
                try:
                    result = engine.ocr(variant_path, cls=True)
                    texts = [lam_sach_dong(t) for t in duyet_text_paddle(result) if lam_sach_dong(t)]
                except Exception as exc:
                    print(f"[WARN] PaddleOCR lỗi với {variant_path}, lang={lang}: {exc}")
                    texts = []
                if texts:
                    return hau_xu_ly_loi_chung("\n".join(texts))
    finally:
        xoa_anh_bien_the(image_path, image_variants, cau_hinh)
    return ""
