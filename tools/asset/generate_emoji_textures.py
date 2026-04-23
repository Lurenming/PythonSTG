"""
generate_emoji_textures.py
──────────────────────────
为弹幕 emoji 系统预生成 96×96 RGBA PNG 纹理。

运行方式（在项目根目录）：
    python tools/asset/generate_emoji_textures.py

输出：assets/images/emoji/{codepoint}.png
  如：1f602.png（😂）  1f621.png（😡）  1f4a9.png（💩）  1f605.png（😅）

策略（按优先级）：
  1. 本地已有文件 → 跳过
  2. Twemoji CDN（jsdelivr）→ 下载 72×72 PNG 并缩放到 96×96
  3. 本地 NotoColorEmoji 字体（若已安装）→ PIL 渲染
  4. 纯色圆 + 文字回退（保证一定能生成）
"""
import os
import sys
import urllib.request
import urllib.error

# ── 目标 emoji 配置 ───────────────────────────────────────────────────────────
EMOJIS: list[tuple[str, str]] = [
    ("😂", "1f602"),
    ("😡", "1f621"),
    ("💩", "1f4a9"),
    ("😅", "1f605"),
]

OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "assets", "images", "emoji"
)
TARGET_SIZE = 96

# Twemoji CDN（Twitter/X 开源 emoji 图集，CC-BY 4.0）
TWEMOJI_URL = (
    "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/{}.png"
)

# 本地 emoji 字体候选
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto-cjk/NotoColorEmoji.ttf",
    "C:/Windows/Fonts/seguiemj.ttf",
    "/System/Library/Fonts/Apple Color Emoji.ttc",
]

_FALLBACK_COLORS = {
    "😂": (255, 220, 50),
    "😡": (255, 60, 60),
    "💩": (130, 85, 30),
    "😅": (100, 200, 255),
}
_FALLBACK_LETTERS = {
    "😂": "XD",
    "😡": ">_<",
    "💩": "poo",
    "😅": "swt",
}
_FALLBACK_TEXT_COLORS = {
    "😂": (80, 60, 0),
    "😡": (255, 255, 255),
    "💩": (255, 240, 200),
    "😅": (0, 60, 120),
}


# ── 生成策略 ──────────────────────────────────────────────────────────────────

def _download_twemoji(codepoint: str, dest: str) -> bool:
    """从 Twemoji CDN 下载并缩放到 TARGET_SIZE，返回是否成功。"""
    from PIL import Image
    import io

    url = TWEMOJI_URL.format(codepoint)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pystg-emoji-tool/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        img = img.resize((TARGET_SIZE, TARGET_SIZE), Image.LANCZOS)
        img.save(dest, "PNG")
        return True
    except (urllib.error.URLError, OSError, Exception) as e:
        print(f"    ↳ Twemoji 下载失败: {e}")
        return False


def _render_with_font(emoji_char: str, dest: str) -> bool:
    """使用本地 NotoColorEmoji 字体渲染，返回是否成功。"""
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np

    for path in _FONT_CANDIDATES:
        if not os.path.exists(path):
            continue
        try:
            font = ImageFont.truetype(path, TARGET_SIZE - 8)
        except Exception:
            continue

        img = Image.new("RGBA", (TARGET_SIZE, TARGET_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            draw.text((4, 2), emoji_char, font=font, embedded_color=True)
        except TypeError:
            draw.text((4, 2), emoji_char, font=font)

        arr = np.array(img)
        if arr[:, :, 3].max() > 10:
            img.save(dest, "PNG")
            print(f"    ↳ 使用本地字体: {path}")
            return True

    return False


def _render_fallback(emoji_char: str, dest: str) -> None:
    """纯色圆 + 文字回退（保证生成），风格与 GL 渲染器回退一致。"""
    from PIL import Image, ImageDraw, ImageFont

    s = TARGET_SIZE
    bg = _FALLBACK_COLORS.get(emoji_char, (180, 180, 180))
    label = _FALLBACK_LETTERS.get(emoji_char, "?")
    fg = _FALLBACK_TEXT_COLORS.get(emoji_char, (0, 0, 0))

    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 外圈阴影
    draw.ellipse([2, 2, s - 2, s - 2], fill=(0, 0, 0, 80))
    # 主圆
    draw.ellipse([4, 4, s - 4, s - 4], fill=(*bg, 235))
    # 高光
    draw.ellipse([14, 10, 36, 28], fill=(255, 255, 255, 60))

    # 文字（尝试 DejaVu，回退到内置 default）
    font_path_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    font = None
    for fp in font_path_candidates:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, s // 3)
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default(size=s // 4)

    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((s - tw) // 2, (s - th) // 2), label, font=font, fill=(*fg, 255))

    img.save(dest, "PNG")
    print(f"    ↳ 使用纯色回退（无 emoji 字体，无网络）")


# ── 主流程 ────────────────────────────────────────────────────────────────────

def generate_all(force: bool = False) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"输出目录: {os.path.abspath(OUTPUT_DIR)}")
    print()

    for emoji_char, codepoint in EMOJIS:
        dest = os.path.join(OUTPUT_DIR, f"{codepoint}.png")
        print(f"[{emoji_char}]  {codepoint}.png")

        if os.path.exists(dest) and not force:
            print(f"    ↳ 已存在，跳过（用 --force 强制重新生成）")
            continue

        # 策略 1：Twemoji CDN
        if _download_twemoji(codepoint, dest):
            print(f"    ↳ Twemoji 下载成功 ✓")
            continue

        # 策略 2：本地字体
        if _render_with_font(emoji_char, dest):
            print(f"    ↳ 本地字体渲染成功 ✓")
            continue

        # 策略 3：纯色回退
        _render_fallback(emoji_char, dest)
        print(f"    ↳ 回退渲染完成 ✓")

    print()
    print("所有 emoji 纹理已就绪。")


if __name__ == "__main__":
    force = "--force" in sys.argv
    generate_all(force=force)
