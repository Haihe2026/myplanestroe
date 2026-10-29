"""Local image composition with exact copy and checked file exports."""
import argparse
import io
import json
import math
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps

PRESETS = {
    "portrait-cover": {"width": 1080, "height": 1440, "band": "top", "band_ratio": 0.30},
    "square-post": {"width": 1080, "height": 1080, "band": "bottom", "band_ratio": 0.28},
    "wide-banner": {"width": 1600, "height": 900, "band": "left", "band_ratio": 0.40},
    "vertical-story": {"width": 1080, "height": 1920, "band": "bottom", "band_ratio": 0.28},
}


def resolve_config(cfg):
    if not isinstance(cfg, dict):
        raise ValueError("Each output must be an object")
    preset = cfg.get("preset")
    if preset is not None and preset not in PRESETS:
        raise ValueError("Unknown preset")
    return {**PRESETS.get(preset, {}), **cfg}


def integer(value, label, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label} must be an integer from {low} to {high}")
    return value


def number(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{label} must be from {low} to {high}")
    return value


def font_path(spec, base, text):
    if spec.get("font"):
        p = Path(spec["font"])
        p = p if p.is_absolute() else base / p
        if not p.is_file():
            raise ValueError("The requested font file does not exist")
        return str(p)
    cjk = any(ord(c) > 0x2FFF for c in text)
    root = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    candidates = [root / "msyh.ttc", root / "simhei.ttf", Path("/System/Library/Fonts/PingFang.ttc"), Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")]
    if not cjk:
        candidates.extend([root / "arial.ttf", Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")])
    for p in candidates:
        if p.is_file():
            return str(p)
    raise ValueError("No suitable local font found; specify a font file supporting the copy")


def wrap(text, font, width):
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for token in re.findall(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*|[^A-Za-z0-9]", paragraph):
            if font.getlength(line + token) <= width:
                line += token
                continue
            closing = '，。！？；：、）》】」』…,.!?;:'
            opening = '（《【「『('
            if line and ((len(token) == 1 and token in closing) or line[-1] in opening):
                tail = line[-1]
                if len(line) > 1 and font.getlength(tail + token) <= width:
                    lines.append(line[:-1])
                    line = tail + token
                    continue
            if line:
                lines.append(line)
                line = ""
            for char in token:
                if font.getlength(line + char) > width:
                    if not line:
                        raise ValueError("A character cannot fit in the text area")
                    lines.append(line)
                    line = ""
                line += char
        if len(line) == 1 and len(paragraph) > 1 and lines and len(lines[-1]) > 2:
            tail = lines[-1][-1]
            if font.getlength(tail + line) <= width and tail not in '，。！？；：、,.!?;:':
                lines[-1] = lines[-1][:-1]
                line = tail + line
        lines.append(line)
    return lines


def fit_copy(title, subtitle, fontfile, width, height, maxsize):
    for size in range(maxsize, 13, -1):
        main = ImageFont.truetype(fontfile, size)
        sub = ImageFont.truetype(fontfile, max(14, round(size * 0.52)))
        tl = wrap(title, main, width) if title else []
        sl = wrap(subtitle, sub, width) if subtitle else []
        mh = sum(main.getmetrics()) + max(2, round(size * 0.15))
        sh = sum(sub.getmetrics()) + max(2, round(size * 0.1))
        gap = round(size * 0.3) if tl and sl else 0
        used = len(tl) * mh + len(sl) * sh + gap
        if used <= height:
            return main, sub, tl, sl, mh, sh, gap, used
    raise ValueError("Full copy cannot fit; increase the text band or canvas; no text was truncated")


def render(image, spec, cfg, fontfile, output):
    cfg = resolve_config(cfg)
    width = integer(cfg.get("width"), "width", 128, 4096)
    height = integer(cfg.get("height"), "height", 128, 4096)
    if width * height > 16000000:
        raise ValueError("Canvas exceeds 16 million pixels")
    fmt = cfg.get("format", "png").lower()
    fmt = "jpeg" if fmt == "jpg" else fmt
    if fmt not in ("png", "jpeg"):
        raise ValueError("format must be png or jpeg")
    fit = cfg.get("fit", "contain")
    band = cfg.get("band", "bottom")
    if fit not in ("contain", "cover") or band not in ("top", "bottom", "left", "right"):
        raise ValueError("Invalid fit or band")
    anchor = cfg.get("anchor", [0.5, 0.5])
    if not isinstance(anchor, list) or len(anchor) != 2:
        raise ValueError("anchor needs two numbers")
    anchor = tuple(number(v, "anchor", 0, 1) for v in anchor)
    ratio = number(cfg.get("band_ratio", 0.28), "band_ratio", 0.15, 0.55)
    title, subtitle = spec.get("title", ""), spec.get("subtitle", "")
    padding = cfg.get("safe_margin", [0, 0, 0, 0])
    if not isinstance(padding, list) or len(padding) != 4:
        raise ValueError("safe_margin must be [top, right, bottom, left] pixels")
    top, right, bottom, left = [integer(v, "safe_margin", 0, 4096) for v in padding]
    inner_w, inner_h = width-left-right, height-top-bottom
    if min(inner_w, inner_h) < 128:
        raise ValueError("Safe margins leave too little usable canvas")
    horizontal = band in ("left", "right")
    bh = round((inner_w if horizontal else inner_h) * ratio) if title or subtitle else 0
    area = (inner_w-bh, inner_h) if horizontal else (inner_w, inner_h-bh)
    align = cfg.get("text_align", "left")
    if align not in ("left", "center", "right"):
        raise ValueError("text_align must be left, center or right")
    bg = ImageColor.getrgb(spec.get("background", "#FFFFFF"))
    fg = ImageColor.getrgb(spec.get("foreground", "#172A2A"))
    accent = ImageColor.getrgb(spec.get("accent", "#168575"))
    canvas = Image.new("RGB", (width, height), bg)
    scale = (max if fit == "cover" else min)(area[0] / image.width, area[1] / image.height)
    if fit == "cover":
        placed = ImageOps.fit(image, area, Image.Resampling.LANCZOS, centering=anchor)
    else:
        placed = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.LANCZOS)
    ix = left + (bh if band == "left" else 0)
    iy = top + (bh if band == "top" else 0)
    canvas.paste(placed, (ix+(area[0]-placed.width)//2, iy+(area[1]-placed.height)//2), placed)
    copy_data = {}
    if bh:
        margin = max(12, round(min(width, height) * 0.045))
        bw, band_h = (bh, inner_h) if horizontal else (inner_w, bh)
        tx = left + (inner_w-bh if band == "right" else 0)
        by = top + (inner_h-bh if band == "bottom" else 0)
        main, sub, tl, sl, mh, sh, gap, used = fit_copy(title, subtitle, fontfile, bw - 2 * margin, band_h - 2 * margin, max(14, min(110, round(width * 0.068))))
        draw = ImageDraw.Draw(canvas)
        y = by + (band_h - used) // 2
        draw.rectangle((tx+margin, by + 7, tx+margin + min(max(20, width // 12), bw-2*margin), by + 11), fill=accent)
        def text_x(line, font):
            spare = bw-2*margin-font.getlength(line)
            return tx+margin+(spare/2 if align == "center" else spare if align == "right" else 0)
        for line in tl:
            draw.text((text_x(line, main), y), line, font=main, fill=fg, anchor="lt")
            y += mh
        y += gap
        for line in sl:
            draw.text((text_x(line, sub), y), line, font=sub, fill=fg, anchor="lt")
            y += sh
        copy_data = {"title_lines": tl, "subtitle_lines": sl, "title_font_size": main.size, "subtitle_font_size": sub.size}
    limit = cfg.get("max_kb")
    if limit is not None:
        number(limit, "max_kb", 1, 100000)
        if fmt != "jpeg":
            raise ValueError("max_kb is supported only for JPEG")
    quality = None
    if fmt == "jpeg":
        for q in range(95, 34, -5):
            stream = io.BytesIO()
            canvas.save(stream, format="JPEG", quality=q, optimize=True)
            if limit is None or stream.tell() <= limit * 1024:
                output.write_bytes(stream.getvalue())
                quality = q
                break
        else:
            raise ValueError("JPEG cannot meet max_kb at quality >=35; increase the limit or choose smaller dimensions")
    else:
        canvas.save(output, format="PNG", optimize=True)
    warnings = []
    if scale > 1.01:
        warnings.append("Source enlarged by interpolation; no new detail recovered")
    if fit == "cover" and abs(image.width / image.height - area[0] / area[1]) > 0.001:
        warnings.append("Source cropped; inspect subject boundaries")
    return {"file": output.name, "width": width, "height": height, "format": fmt, "bytes": output.stat().st_size, "jpeg_quality": quality, "warnings": warnings, "band": band, "text_align": align, "safe_margin": padding, "image_area": [ix,iy,area[0],area[1]], **copy_data}


def contact_sheet(staging, outputs):
    columns = min(3, len(outputs))
    sheet = Image.new("RGB", (columns*360, math.ceil(len(outputs)/columns)*320), "#EEF1F3")
    draw = ImageDraw.Draw(sheet)
    for index, item in enumerate(outputs):
        x, y = (index % columns)*360, (index // columns)*320
        with Image.open(staging/item["file"]) as opened:
            thumb = ImageOps.contain(opened.convert("RGB"), (336,270), Image.Resampling.LANCZOS)
        sheet.paste(thumb,(x+(360-thumb.width)//2,y+12+(270-thumb.height)//2))
        draw.text((x+12,y+290), f'{index+1}. {item["width"]}x{item["height"]} {item["format"]}', fill="#202529")
    sheet.save(staging/"contact-sheet.png", optimize=True)


def run(spec_path, destination):
    spec_path, destination = Path(spec_path).resolve(), Path(destination).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    if destination.exists():
        raise ValueError("Output directory already exists; choose a new directory")
    for key in ("title", "subtitle"):
        if not isinstance(spec.get(key, ""), str):
            raise ValueError(f"{key} must be text")
    outputs = spec.get("outputs")
    if not isinstance(outputs, list) or not 1 <= len(outputs) <= 12:
        raise ValueError("outputs must contain 1 to 12 items")
    outputs = [resolve_config(cfg) for cfg in outputs]
    if type(spec.get("preview", True)) is not bool:
        raise ValueError("preview must be true or false")
    names = [c.get("name", "") for c in outputs]
    if any(not isinstance(n, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", n) or n.upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]} for n in names) or len(set(n.lower() for n in names)) != len(names):
        raise ValueError("Output names must be unique safe filenames")
    if any(n.lower() == "contact-sheet" for n in names):
        raise ValueError("contact-sheet is reserved for preview")
    source = Path(spec["image"])
    source = source if source.is_absolute() else spec_path.parent / source
    with Image.open(source) as opened:
        if getattr(opened, "n_frames", 1) != 1:
            raise ValueError("Animated/multipage images require selecting one frame first")
        image = ImageOps.exif_transpose(opened).convert("RGBA")
    text = spec.get("title", "") + spec.get("subtitle", "")
    fontfile = font_path(spec, spec_path.parent, text) if text else None
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".image-finish-", dir=destination.parent))
    try:
        manifest = {"source": source.name, "source_size": list(image.size), "title": spec.get("title", ""), "subtitle": spec.get("subtitle", ""), "outputs": []}
        for cfg in outputs:
            ext = ".jpg" if cfg.get("format", "png").lower() in ("jpg", "jpeg") else ".png"
            manifest["outputs"].append(render(image, spec, cfg, fontfile, staging / (cfg["name"] + ext)))
        if spec.get("preview", True):
            contact_sheet(staging, manifest["outputs"])
            manifest["preview"] = "contact-sheet.png"
        (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        if destination.exists():
            raise ValueError("Output directory appeared during processing")
        staging.rename(destination)
        return manifest
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        result = run(args.spec, args.out)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Image finish failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
