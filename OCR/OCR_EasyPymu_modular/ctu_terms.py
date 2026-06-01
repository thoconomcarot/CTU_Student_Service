"""
ctu_terms.py
Từ điển sửa lỗi chính tả/thuật ngữ thường gặp trong tài liệu CTU.

Mục tiêu: sửa các lỗi OCR có tính lặp lại theo domain Trường Đại học Cần Thơ,
không hard-code theo từng file riêng lẻ.
"""

from __future__ import annotations

import re

# Dạng regex -> từ chuẩn. Các rule nên đủ hẹp để tránh sửa nhầm nội dung bình thường.
CTU_TERM_RULES: list[tuple[str, str]] = [
    (r"\bDai\s*hoc\s*Can\s*Tho\b", "Đại học Cần Thơ"),
    (r"\bD[aạ]i\s*h[oọ]c\s*C[aầ]n\s*Th[oơ]\b", "Đại học Cần Thơ"),
    (r"\bTruong\s*Dai\s*hoc\s*Can\s*Tho\b", "Trường Đại học Cần Thơ"),
    (r"\bTrường\s+Đại\s+học\s+Cần\s+Thơ\b", "Trường Đại học Cần Thơ"),
    (r"\bD\s*H\s*C\s*T\b", "ĐHCT"),
    (r"\bĐ\s*H\s*C\s*T\b", "ĐHCT"),
    (r"\bCTSV\b", "CTSV"),
    (r"\bPh[oò]ng\s+C[oô]ng\s+t[aá]c\s+Sinh\s+vi[eê]n\b", "Phòng Công tác Sinh viên"),
    (r"\bTrung\s+t[aâ]m\s+Ph[uụ]c\s+v[uụ]\s+Sinh\s+vi[eê]n\b", "Trung tâm Phục vụ Sinh viên"),
    (r"\bC[oô]ng\s+t[aá]c\s+h[oọ]c\s+v[uụ]\b", "công tác học vụ"),
    (r"\bh[oọ]c\s+v[uụ]\b", "học vụ"),
    (r"\bsinh\s+vi[eê]n\b", "sinh viên"),
    (r"\bgi[aả]ng\s+vi[eê]n\b", "giảng viên"),
    (r"\bc[oố]\s+v[aấ]n\s+h[oọ]c\s+t[aậ]p\b", "cố vấn học tập"),
    (r"\bch[ií]nh\s+quy\b", "chính quy"),
    (r"\bh[oọ]c\s+ph[aầ]n\b", "học phần"),
    (r"\bt[ií]n\s+ch[iỉ]\b", "tín chỉ"),
    (r"\bh[oọ]c\s+k[yỳ]\b", "học kỳ"),
    (r"\bk[yý]\s+t[uú]c\s+x[aá]\b", "ký túc xá"),
    (r"\bmi[eễ]n\s+gi[aả]m\s+h[oọ]c\s+ph[ií]\b", "miễn giảm học phí"),
    (r"\bh[oọ]c\s+b[oổ]ng\b", "học bổng"),
    (r"\bđi[eể]m\s+r[eè]n\s+luy[eệ]n\b", "điểm rèn luyện"),
    (r"\bt[aạ]m\s+ho[aã]n\s+ngh[iĩ]a\s+v[uụ]\s+qu[aâ]n\s+s[uự]\b", "tạm hoãn nghĩa vụ quân sự"),
]


def apply_ctu_term_fixes(text: str) -> str:
    """Sửa lỗi thuật ngữ CTU theo danh sách rule dùng chung."""

    if not text:
        return ""

    for pattern, replacement in CTU_TERM_RULES:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text
