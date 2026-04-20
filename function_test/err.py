import numpy as np
from importlib import import_module
from pathlib import Path
import math
import random

try:
    # MoviePy >= 2.0
    from moviepy import VideoClip
except ImportError:
    # MoviePy 1.x
    VideoClip = import_module("moviepy.editor").VideoClip
from PIL import Image, ImageDraw, ImageFont

# --- 基本配置 ---
W, H = 1920, 1080
FPS = 30
DUR_ERROR = 1.0  # 报错滚屏持续时间（秒）
DUR_TEXT = 5.0   # 字符画持续时间（秒）
TOTAL_DUR = DUR_ERROR + DUR_TEXT

# 自动选择一个存在的中文字体路径（Windows / Linux 常见路径）
FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

TERMINAL_FONT_CANDIDATES = [
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/cascadiamono.ttf",
    "C:/Windows/Fonts/lucon.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]


def pick_font_path(candidates):
    for path in candidates:
        if Path(path).exists():
            return path
    return None


def load_font(candidates, size):
    path = pick_font_path(candidates)
    if path:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


FONT_PATH = pick_font_path(FONT_CANDIDATES)
TERMINAL_FONT_PATH = pick_font_path(TERMINAL_FONT_CANDIDATES)

# --- 准备 Debian 关机/报错日志 ---
ERROR_LOGS = [
    "[  OK  ] Stopped target Timers.",
    "[  OK  ] Stopped target Sockets.",
    "[  OK  ] Closed Syslog Socket.",
    "[FAILED] Failed to unmount /oldroot.",
    "[FAILED] Failed to unmount /home.",
    "[FAILED] Failed to unmount /var/log.",
    "[ TIME ] Timed out waiting for device dev-disk-by\\x2duuid...",
    "[DEPEND] Dependency failed for /mnt/data.",
    "[  12.345] sd 0:0:0:0: [sda] Stopping disk",
    "[  13.001] kvm: exiting hardware virtualization",
    "[  13.050] watchdog: watchdog0: watchdog did not stop!",
    "[  14.221] Kernel panic - not syncing: Attempted to kill init! exitcode=0x00000009",
    "[  14.221] CPU: 0 PID: 1 Comm: systemd-shutdow Not tainted 5.10.0-deb11u1 #1 Debian",
    "[  14.221] Hardware name: Generic PC",
    "[  14.221] Call Trace:",
    "[  14.221]  dump_stack+0x6d/0x8b",
    "[  14.221]  panic+0x101/0x2e3",
    "[  14.221]  do_exit+0xab4/0xab0",
    "[  14.221]  do_group_exit+0x43/0xa0",
    "[  14.221] ---[ end Kernel panic - not syncing: Attempted to kill init! ]---"
]


def build_stream_lines(count=260):
    """构造一批可循环滚动的终端文本。"""
    rng = random.Random(20260418)
    modules = ["render", "asset", "audio", "task", "net", "vm", "cache", "stage", "bullet", "shader"]
    actions = ["init", "flush", "decode", "reload", "attach", "dispatch", "sync", "retry", "mount", "panic"]
    severities = ["INFO", "DEBUG", "WARN", "TRACE", "ERROR"]

    lines = list(ERROR_LOGS)
    for i in range(count):
        ts = f"[{i * 0.071:8.3f}]"
        sev = rng.choice(severities)
        mod = rng.choice(modules)
        act = rng.choice(actions)
        addr = f"0x{rng.randrange(0, 16**8):08x}"
        core = rng.randrange(0, 8)
        code = rng.randrange(10, 999)
        if sev == "ERROR":
            line = f"{ts} {sev} {mod}: {act} failed, errno={code}, ptr={addr}, cpu={core}"
        else:
            line = f"{ts} {sev} {mod}: {act} ok, ticket={code}, ptr={addr}, cpu={core}"
        lines.append(line)
    return lines


STREAM_LINES = build_stream_lines()

def generate_text_mask(text, font_path, font_size=120):
    """将文字渲染为二值掩码，用于后续点阵方块绘制。"""
    if not font_path:
        raise RuntimeError(
            "未找到可用中文字体。请安装中文字体并在 FONT_CANDIDATES 中补充路径。"
        )

    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError as exc:
        raise RuntimeError(f"字体加载失败: {font_path}") from exc

    probe_img = Image.new("L", (1, 1), color=0)
    probe_draw = ImageDraw.Draw(probe_img)
    bbox = probe_draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0] + 8
    height = bbox[3] - bbox[1] + 8

    text_img = Image.new("L", (width, height), color=0)
    text_draw = ImageDraw.Draw(text_img)
    text_draw.text((4 - bbox[0], 4 - bbox[1]), text, font=font, fill=255)

    mask = np.array(text_img) > 64
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return np.zeros((1, 1), dtype=bool)

    return mask[ys.min(): ys.max() + 1, xs.min(): xs.max() + 1]


def shrink_mask(mask, max_cells):
    """限制掩码宽度，避免点阵超出画面。"""
    if mask.shape[1] <= max_cells:
        return mask

    stride = math.ceil(mask.shape[1] / max_cells)
    return mask[::stride, ::stride]


def mask_pixel_size(mask, cell_size, cell_gap):
    step = cell_size + cell_gap
    width = mask.shape[1] * step - cell_gap
    height = mask.shape[0] * step - cell_gap
    return width, height


def draw_mask_as_blocks(draw, mask, x0, y0, cell_size, cell_gap, color):
    step = cell_size + cell_gap
    for y in range(mask.shape[0]):
        py = y0 + y * step
        row = mask[y]
        for x in range(mask.shape[1]):
            if not row[x]:
                continue
            px = x0 + x * step
            draw.rectangle((px, py, px + cell_size - 1, py + cell_size - 1), fill=color)


# --- 预渲染中间两行点阵文字 ---
CELL_SIZE = 5
CELL_GAP = 1
MAX_TEXT_WIDTH = W - 160

max_cells = MAX_TEXT_WIDTH // (CELL_SIZE + CELL_GAP)
line1_mask = shrink_mask(generate_text_mask("九州拾遗第一次音mad合作", FONT_PATH, font_size=124), max_cells)
line2_mask = shrink_mask(generate_text_mask("比寒武更久的梦", FONT_PATH, font_size=136), max_cells)

center_overlay = Image.new("RGBA", (W, H), color=(0, 0, 0, 0))
draw_center = ImageDraw.Draw(center_overlay)

w1, h1 = mask_pixel_size(line1_mask, CELL_SIZE, CELL_GAP)
w2, h2 = mask_pixel_size(line2_mask, CELL_SIZE, CELL_GAP)

line_gap = 44
block_total_h = h1 + h2 + line_gap
CENTER_TEXT_OFFSET_Y = 110
CENTER_TOP = (H - block_total_h) // 2 + CENTER_TEXT_OFFSET_Y
CENTER_TOP = min(CENTER_TOP, H - block_total_h - 36)
CENTER_BOTTOM = CENTER_TOP + block_total_h

# 绘制到画面正中间（绿色，带点复古终端味）
TEXT_COLOR = (72, 255, 110, 255)
GLOW_COLOR = (32, 190, 70, 96)

draw_mask_as_blocks(draw_center, line1_mask, (W - w1) // 2, CENTER_TOP, CELL_SIZE + 2, CELL_GAP, GLOW_COLOR)
draw_mask_as_blocks(draw_center, line2_mask, (W - w2) // 2, CENTER_TOP + h1 + line_gap, CELL_SIZE + 2, CELL_GAP, GLOW_COLOR)
draw_mask_as_blocks(draw_center, line1_mask, (W - w1) // 2, CENTER_TOP, CELL_SIZE, CELL_GAP, TEXT_COLOR)
draw_mask_as_blocks(draw_center, line2_mask, (W - w2) // 2, CENTER_TOP + h1 + line_gap, CELL_SIZE, CELL_GAP, TEXT_COLOR)

LOG_FONT = load_font(TERMINAL_FONT_CANDIDATES, 25)
BG_FONT = load_font(TERMINAL_FONT_CANDIDATES, 21)
BG_FONT_DENSE = load_font(TERMINAL_FONT_CANDIDATES, 17)
HUD_FONT = load_font(TERMINAL_FONT_CANDIDATES, 18)

_yy = np.arange(H, dtype=np.float32)[:, None]
_xx = np.arange(W, dtype=np.float32)[None, :]
SCANLINE_MASK = np.where((_yy.astype(np.int32) % 2) == 0, 1.0, 0.82).astype(np.float32)
_nx = (_xx - (W / 2.0)) / (W / 2.0)
_ny = (_yy - (H / 2.0)) / (H / 2.0)
VIGNETTE_MASK = np.clip(1.05 - 0.30 * (_nx**2 + _ny**2), 0.62, 1.0).astype(np.float32)


def draw_scrolling_stream(
    draw,
    t,
    font,
    speed,
    row_height,
    mode,
    left_margin=20,
    clip_len=120,
    drift=False,
    dynamic_slice=True,
    line_stride=5,
):
    rows = H // row_height + 4
    y_start = -((t * speed) % row_height) - row_height
    phase = int(t * speed / row_height)

    for row in range(rows):
        y = int(y_start + row * row_height)
        line_index = (phase + row * line_stride) % len(STREAM_LINES)
        text = STREAM_LINES[line_index]

        if len(text) > clip_len:
            if dynamic_slice:
                shift = (phase * 7 + row * 11) % (len(text) - clip_len + 1)
                text = text[shift: shift + clip_len]
            else:
                text = text[:clip_len]

        x = left_margin
        if drift:
            x += ((row * 37 + phase * 13) % 130) - 65

        if "FAILED" in text or "panic" in text.lower() or "ERROR" in text:
            color = (250, 96, 80, 238) if mode == "intro" else (154, 64, 56, 170)
        elif "OK" in text:
            color = (110, 250, 130, 232) if mode == "intro" else (82, 192, 106, 182)
        else:
            color = (188, 212, 188, 210) if mode == "intro" else (72, 128, 78, 165)

        draw.text((x, y), text, font=font, fill=color)


def draw_hud_noise(draw, t):
    pulse = int(100 + 40 * math.sin(t * 6.5))
    top_line = f"SYNC={int(t * 1200) % 9999:04d}  VBL={pulse:03d}  FRAME={int(t * FPS):04d}"
    bot_line = "BUS:ff:01  VRAM:OK  IO:0x3f8  MODE:CRT-EMULATED"

    draw.text((22, 18), top_line, font=HUD_FONT, fill=(88, 180, 90, 190))
    draw.text((22, H - 44), bot_line, font=HUD_FONT, fill=(76, 150, 84, 186))


def apply_crt_effect(frame, t):
    arr = frame.astype(np.float32)
    flicker = 0.985 + 0.015 * math.sin(2.0 * math.pi * t * 7.2)

    arr *= flicker
    arr *= SCANLINE_MASK[:, :, None]
    arr *= VIGNETTE_MASK[:, :, None]

    green_hot = np.clip((arr[:, :, 1] - 88.0) / 150.0, 0.0, 1.0)
    arr[:, :, 1] += green_hot * 18.0
    arr[:, :, 0] += green_hot * 4.5
    arr[:, :, 2] += green_hot * 8.0

    return np.clip(arr, 0, 255).astype(np.uint8)


def render_intro_phase(t):
    img = Image.new("RGBA", (W, H), color=(0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    # 第一段使用固定左对齐，营造典型终端报错滚屏感。
    draw_scrolling_stream(
        draw,
        t,
        LOG_FONT,
        speed=460,
        row_height=29,
        mode="intro",
        left_margin=18,
        clip_len=124,
        drift=False,
        dynamic_slice=False,
        line_stride=3,
    )
    draw_hud_noise(draw, t)

    return img


def render_text_phase(t):
    img = Image.new("RGBA", (W, H), color=(0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    # 第二段叠加两层更快的信息流，密度更高、更复古。
    draw_scrolling_stream(
        draw,
        t,
        BG_FONT,
        speed=250,
        row_height=21,
        mode="text",
        left_margin=12,
        clip_len=132,
        drift=False,
        dynamic_slice=True,
        line_stride=4,
    )
    draw_scrolling_stream(
        draw,
        t + 1.37,
        BG_FONT_DENSE,
        speed=340,
        row_height=17,
        mode="text",
        left_margin=8,
        clip_len=144,
        drift=False,
        dynamic_slice=True,
        line_stride=7,
    )
    draw_hud_noise(draw, t + 2.5)

    panel_pad = 48
    draw.rectangle(
        (120, CENTER_TOP - panel_pad, W - 120, CENTER_BOTTOM + panel_pad),
        fill=(0, 0, 0, 208),
        outline=(40, 92, 44, 140),
        width=2,
    )

    img.alpha_composite(center_overlay)
    return img

# --- 渲染每一帧 ---
def make_frame(t):
    if t < DUR_ERROR:
        base = render_intro_phase(t)
    else:
        base = render_text_phase(t - DUR_ERROR)

    return apply_crt_effect(np.array(base.convert("RGB")), t)

# --- 生成视频 ---
print("开始渲染视频，请稍候...")
clip = VideoClip(make_frame, duration=TOTAL_DUR)
clip.write_videofile("linux_ed_output.mp4", fps=FPS, codec="libx264")
print("渲染完成！已保存为 linux_ed_output.mp4")