"""Digital document image and photo extraction with orientation and size normalization."""

import base64
import io
import zipfile
from PIL import Image, ImageOps
import pymupdf  # type: ignore

MAX_DIMENSION = 320
MIN_DIMENSION = 40
MIN_AREA = 2000
MAX_ASPECT_RATIO = 3.5


def optimize_image_bytes(img_bytes: bytes) -> str | None:
    """Validate, orient, resize, and convert image bytes to a compact base64 data URI."""
    try:
        with Image.open(io.BytesIO(img_bytes)) as img:
            img = ImageOps.exif_transpose(img)
            w, h = img.size
            if w < MIN_DIMENSION or h < MIN_DIMENSION or (w * h) < MIN_AREA:
                return None
            aspect = max(w, h) / max(1, min(w, h))
            if aspect > MAX_ASPECT_RATIO:
                return None

            # Downscale if needed to keep payload lightweight and fast
            if max(w, h) > MAX_DIMENSION:
                img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

            out = io.BytesIO()
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                img.save(out, format="PNG", optimize=True)
                mime = "image/png"
            else:
                rgb = img.convert("RGB")
                rgb.save(out, format="JPEG", quality=82, optimize=True)
                mime = "image/jpeg"

            b64_str = base64.b64encode(out.getvalue()).decode("ascii")
            return f"data:{mime};base64,{b64_str}"
    except Exception:
        return None


def extract_picture_from_pdf(doc: pymupdf.Document) -> str | None:
    """Extract candidate photo/picture from digital PDF document.

    Favors images on the first page near the top (header / sidebar) with portrait or square aspect ratios.
    """
    candidates: list[tuple[float, bytes]] = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        image_list = page.get_images(full=True)
        if not image_list:
            continue

        page_height = page.rect.height or 800.0

        for img_info in image_list:
            xref = img_info[0]
            try:
                base_img = doc.extract_image(xref)
                if not base_img or not base_img.get("image"):
                    continue

                raw_bytes = base_img["image"]
                w = base_img.get("width", 0)
                h = base_img.get("height", 0)

                if w < MIN_DIMENSION or h < MIN_DIMENSION or (w * h) < MIN_AREA:
                    continue
                aspect = max(w, h) / max(1, min(w, h))
                if aspect > MAX_ASPECT_RATIO:
                    continue

                # Check position on page
                rects = page.get_image_rects(xref)
                y0 = rects[0].y0 if rects else (page_height / 2.0)

                # Avoid full-background banners or page-covering watermarks
                if rects and page.rect.width and page.rect.height:
                    img_area = rects[0].width * rects[0].height
                    page_area = page.rect.width * page.rect.height
                    if (img_area / page_area) > 0.85:
                        continue

                # Score image:
                # 1. Page 0 is heavily favored (+1000)
                # 2. Upper half of page 0 is favored (+500 if y0 < page_height * 0.6)
                # 3. Portrait or square aspect ratio 0.6 <= w/h <= 1.6 (+300)
                score = 0.0
                if page_idx == 0:
                    score += 1000.0
                    if y0 < page_height * 0.6:
                        score += 500.0
                else:
                    score += max(0.0, 500.0 - page_idx * 100.0)

                ratio = w / max(1, h)
                if 0.6 <= ratio <= 1.6:
                    score += 300.0

                candidates.append((score, raw_bytes))
            except Exception:
                continue

        # If we found candidate pictures on page 1, don't search all remaining pages
        if page_idx == 0 and candidates:
            break

    if not candidates:
        return None

    # Sort by score descending
    candidates.sort(key=lambda c: c[0], reverse=True)
    for _, raw_bytes in candidates:
        data_uri = optimize_image_bytes(raw_bytes)
        if data_uri:
            return data_uri

    return None


def extract_picture_from_docx(docx_bytes: bytes) -> str | None:
    """Extract candidate photo from DOCX media archive."""
    try:
        candidates: list[tuple[float, bytes]] = []
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
            media_files = [n for n in zf.namelist() if n.startswith("word/media/")]
            for idx, name in enumerate(media_files):
                data = zf.read(name)
                try:
                    with Image.open(io.BytesIO(data)) as img:
                        w, h = img.size
                        if w < MIN_DIMENSION or h < MIN_DIMENSION or (w * h) < MIN_AREA:
                            continue
                        aspect = max(w, h) / max(1, min(w, h))
                        if aspect > MAX_ASPECT_RATIO:
                            continue

                        score = 100.0 - idx * 10.0
                        ratio = w / max(1, h)
                        if 0.6 <= ratio <= 1.6:
                            score += 200.0
                        candidates.append((score, data))
                except Exception:
                    continue

        if not candidates:
            return None

        candidates.sort(key=lambda c: c[0], reverse=True)
        for _, raw_bytes in candidates:
            data_uri = optimize_image_bytes(raw_bytes)
            if data_uri:
                return data_uri
    except Exception:
        return None

    return None
