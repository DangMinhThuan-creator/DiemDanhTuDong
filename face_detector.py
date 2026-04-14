"""
face_detector.py — Nhận diện & phân tích khuôn mặt
====================================================
Module xử lý toàn bộ logic nhận diện khuôn mặt:
  - Phát hiện khuôn mặt bằng Haar Cascade (OpenCV)
  - Nhận diện danh tính bằng DeepFace (Facenet512)
  - Phân tích cảm xúc / tuổi / giới tính
  - Vẽ overlay kết quả lên frame camera

Các hàm:
    detect_faces_haar(frame)           — Phát hiện vị trí khuôn mặt
    recognize_faces(frame, db_path)    — Nhận diện danh tính
    analyze_face(frame_or_roi)         — Phân tích cảm xúc/tuổi/giới tính
    draw_face_box(frame, ...)          — Vẽ khung + nhãn lên frame
    draw_header(frame, text)           — Vẽ thanh tiêu đề
    draw_footer(frame, msg, color, n)  — Vẽ thanh trạng thái
"""

import cv2
import numpy as np
from deepface import DeepFace
from pathlib import Path

from config import (
    MODEL_NAME, DETECTOR, DISTANCE_METRIC, THRESHOLD,
    COLOR_SUCCESS, COLOR_UNKNOWN, COLOR_ERROR, COLOR_INFO,
    DB_PATH,
)


# ============================================================
# HAAR CASCADE — PHÁT HIỆN KHUÔN MẶT NHANH
# ============================================================
_face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
_eye_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_eye.xml"
)


def detect_faces_haar(frame: np.ndarray) -> list[tuple]:
    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = _face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60),
        flags=cv2.CASCADE_SCALE_IMAGE,
    )
    return list(faces) if len(faces) > 0 else []


def detect_eyes_in_roi(roi_gray: np.ndarray) -> list[tuple]:
    eyes = _eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=5)
    return list(eyes) if len(eyes) > 0 else []


# ============================================================
# DEEPFACE — NHẬN DIỆN DANH TÍNH
# ============================================================
def _find_col(row, keywords: list[str]) -> str | None:
    """Tìm tên cột đầu tiên chứa bất kỳ keyword nào (không phân biệt hoa/thường)."""
    for col in row.index:
        if any(k in col.lower() for k in keywords):
            return col
    return None


def recognize_faces(frame: np.ndarray, db_path: Path = DB_PATH) -> list[dict]:
    """
    Nhận diện danh tính khuôn mặt bằng DeepFace.find().

    Returns:
        List[dict] mỗi phần tử là:
        {
            "member_id" : str,
            "distance"  : float,
            "confidence": float,
            "x1", "y1", "x2", "y2": int
        }
    """
    results = []
    try:
        matches = DeepFace.find(
            img_path=frame,
            db_path=str(db_path),
            model_name=MODEL_NAME,
            detector_backend=DETECTOR,
            distance_metric=DISTANCE_METRIC,
            enforce_detection=False,
            silent=True,
        )
    except Exception as e:
        if "Face could not be detected" not in str(e):
            print(f"[face_detector] Loi nhan dien: {e}")
        return results

    for face_df in matches:
        if face_df.empty:
            continue

        best = face_df.iloc[0]

        # ── Tìm cột distance ──────────────────────────────────
        # Ưu tiên tên chuẩn trước, fallback sang quét keyword
        preferred = f"{MODEL_NAME}_{DISTANCE_METRIC}"
        dist_col  = preferred if preferred in best.index else _find_col(
            best, ["distance", "cosine", "euclidean", "l2"]
        )
        if dist_col is None:
            print(f"[face_detector] Khong tim thay cot distance. Cac cot: {list(best.index)}")
            continue

        # ── Tìm cột identity ──────────────────────────────────
        id_col = "identity" if "identity" in best.index else _find_col(
            best, ["identity", "path"]
        )
        if id_col is None:
            print(f"[face_detector] Khong tim thay cot identity. Cac cot: {list(best.index)}")
            continue

        distance = float(best[dist_col])
        if distance > THRESHOLD:
            continue

        member_id  = Path(best[id_col]).parent.name
        confidence = round((1 - distance) * 100, 1)

        x1 = int(best.get("source_x", 0))
        y1 = int(best.get("source_y", 0))
        x2 = x1 + int(best.get("source_w", 120))
        y2 = y1 + int(best.get("source_h", 120))

        results.append({
            "member_id" : member_id,
            "distance"  : distance,
            "confidence": confidence,
            "x1": x1, "y1": y1,
            "x2": x2, "y2": y2,
        })

    return results


# ============================================================
# DEEPFACE — PHÂN TÍCH CẢM XÚC / TUỔI / GIỚI TÍNH
# ============================================================
def analyze_face(image) -> dict | None:
    try:
        result = DeepFace.analyze(
            img_path=image,
            actions=["age", "gender", "emotion", "race"],
            enforce_detection=False,
            silent=True,
        )
        if isinstance(result, list):
            result = result[0]
        return result
    except Exception:
        return None


def analyze_face_from_roi(frame: np.ndarray, x1: int, y1: int,
                          x2: int, y2: int) -> dict | None:
    roi = frame[max(0, y1):y2, max(0, x1):x2]
    if roi.size == 0:
        return None
    return analyze_face(roi)


# ============================================================
# VẼ KẾT QUẢ LÊN FRAME
# ============================================================
def draw_face_box(frame: np.ndarray, x1: int, y1: int, x2: int, y2: int,
                  label: str = "", color=COLOR_SUCCESS,
                  analysis: dict = None):
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    if label:
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
        cv2.rectangle(frame, (x1, y1 - th - 12), (x1 + tw + 8, y1), color, -1)
        cv2.putText(frame, label, (x1 + 4, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (10, 10, 10), 2)

    if analysis:
        info = (f"Tuoi: {analysis.get('age', '?')}  |  "
                f"{analysis.get('dominant_gender', '')}  |  "
                f"{analysis.get('dominant_emotion', '')}")
        cv2.putText(frame, info, (x1, y2 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, COLOR_INFO, 1)


def draw_unknown_box(frame: np.ndarray, x: int, y: int, w: int, h: int):
    cv2.rectangle(frame, (x, y), (x + w, y + h), COLOR_UNKNOWN, 2)
    cv2.putText(frame, "Khong xac dinh", (x, y - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_UNKNOWN, 2)


def draw_header(frame: np.ndarray, text: str):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 52), (18, 18, 18), -1)
    cv2.putText(frame, text, (14, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.76, (220, 220, 220), 2)


def draw_footer(frame: np.ndarray, msg: str, color, count: int):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, h - 50), (w, h), (18, 18, 18), -1)
    cv2.putText(frame, msg, (14, h - 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
    counter_text = f"Da diem danh: {count}"
    cv2.putText(frame, counter_text, (w - 220, h - 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, COLOR_SUCCESS, 2)