"""
立绘编辑器 - 主循环与渲染

GLFW + ModernGL + imgui
左侧 imgui 面板（参数调节），右侧游戏分辨率预览。
支持锚点拖拽、角色/表情选择、实时焦点效果预览。
"""

import sys
import os
import json

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, root)
os.chdir(root)

import glfw
import moderngl
import numpy as np
import imgui
from PIL import Image, ImageEnhance

from tools.main_menu_editor.imgui_bridge import create_glfw_renderer, frame_begin, frame_end
from tools.portrait_editor.layout_model import (
    default_layout,
    load_layout,
    save_layout,
    load_characters,
    GAME_VIEW_W as LAYOUT_GAME_VIEW_W,
    GAME_VIEW_H as LAYOUT_GAME_VIEW_H,
)

GAME_VIEW_W = LAYOUT_GAME_VIEW_W
GAME_VIEW_H = LAYOUT_GAME_VIEW_H
PANEL_W = 320
# Default window: panel + game viewport at 1:1, so preview needs no scaling at startup.
EDITOR_W = PANEL_W + GAME_VIEW_W
EDITOR_H = GAME_VIEW_H
CHAR_DIR = os.path.join(root, "assets", "images", "character")


def _find_anchor_ratio(pinfo, width, height):
    anchor = pinfo.get("anchor")
    if anchor is None:
        anchor = pinfo.get("center", [0.5, 0.95])
    if not isinstance(anchor, (list, tuple)) or len(anchor) < 2:
        return 0.5, 0.95
    ax = float(anchor[0])
    ay = float(anchor[1])
    if ax > 1.0:
        ax = ax / max(1.0, float(width))
    if ay > 1.0:
        ay = ay / max(1.0, float(height))
    return max(0.0, min(1.0, ax)), max(0.0, min(1.0, ay))


def _load_portrait_surface(char_cfg, portrait_key):
    """加载单个立绘的 PIL Image（带效果前的原始图）"""
    portraits = char_cfg.get("portraits", {})
    # 先找精确 key，再找 fallback
    pinfo = portraits.get(portrait_key)
    if pinfo is None:
        # fallback to default
        default_key = char_cfg.get("default_portrait", "normal")
        pinfo = portraits.get(default_key)
    if pinfo is None:
        pinfo = portraits.get("Happy") or portraits.get("Normal")
    if pinfo is None:
        return None, None, (0.5, 0.95)
    rel_file = pinfo.get("file", "")
    full_path = os.path.join(CHAR_DIR, rel_file)
    if not os.path.exists(full_path):
        return None, None, (0.5, 0.95)
    img = Image.open(full_path).convert("RGBA")
    anchor = _find_anchor_ratio(pinfo, img.width, img.height)
    return img, pinfo, anchor


def _apply_effects(src_img, saturation, alpha, target_size=None):
    """将效果（饱和度、透明度、缩放）应用到 PIL Image"""
    img = src_img.copy()
    if target_size:
        img = img.resize((target_size[0], target_size[1]), Image.LANCZOS)
    if abs(saturation - 1.0) > 1e-4:
        img = ImageEnhance.Color(img).enhance(max(0.0, saturation))
    if abs(alpha - 1.0) > 1e-4:
        r, g, b, a = img.split()
        a = a.point(lambda p: int(max(0, min(255, p * alpha))))
        img.putalpha(a)
    return img


def _pil_to_mgl_texture(ctx, pil_img):
    """将 PIL RGBA Image 转为 ModernGL 纹理"""
    data = pil_img.tobytes("raw", "RGBA")
    tex = ctx.texture(pil_img.size, 4, data)
    tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
    return tex


def _create_blit_program(ctx):
    vs = (
        "#version 330\n"
        "in vec2 in_pos;\n"
        "in vec2 in_uv;\n"
        "out vec2 v_uv;\n"
        "void main() {\n"
        "    gl_Position = vec4(in_pos * 2.0 - 1.0, 0.0, 1.0);\n"
        "    v_uv = in_uv;\n"
        "}\n"
    )
    fs = (
        "#version 330\n"
        "uniform sampler2D u_tex;\n"
        "in vec2 v_uv;\n"
        "out vec4 f_color;\n"
        "void main() {\n"
        "    f_color = texture(u_tex, vec2(v_uv.x, 1.0 - v_uv.y));\n"
        "}\n"
    )
    prog = ctx.program(vertex_shader=vs, fragment_shader=fs)
    vertices = np.array([
        0, 0, 0, 1,
        0, 1, 0, 0,
        1, 0, 1, 1,
        1, 0, 1, 1,
        0, 1, 0, 0,
        1, 1, 1, 0,
    ], dtype='f4')
    vbo = ctx.buffer(vertices.tobytes())
    vao = ctx.vertex_array(prog, [(vbo, '2f 2f', 'in_pos', 'in_uv')])
    return prog, vao


def _create_portrait_program(ctx):
    """绘制带锚点的立绘四边形"""
    vs = (
        "#version 330\n"
        "uniform vec2 u_anchor;\n"
        "uniform vec2 u_screen;\n"
        "in vec2 in_pos;\n"
        "in vec2 in_uv;\n"
        "out vec2 v_uv;\n"
        "void main() {\n"
        "    v_uv = in_uv;\n"
        "    vec2 normalized = (u_anchor + in_pos) / u_screen;\n"
        "    gl_Position = vec4(normalized.x * 2.0 - 1.0, (1.0 - normalized.y) * 2.0 - 1.0, 0.0, 1.0);\n"
        "}\n"
    )
    fs = (
        "#version 330\n"
        "uniform sampler2D u_tex;\n"
        "in vec2 v_uv;\n"
        "out vec4 f_color;\n"
        "void main() {\n"
        "    f_color = texture(u_tex, v_uv);\n"
        "    if (f_color.a < 0.01) discard;\n"
        "}\n"
    )
    return ctx.program(vertex_shader=vs, fragment_shader=fs)


def _create_color_line_program(ctx):
    """用于绘制编辑器覆盖线框（边框/十字）。"""
    vs = (
        "#version 330\n"
        "uniform vec2 u_screen;\n"
        "in vec2 in_pos;\n"
        "void main() {\n"
        "    vec2 ndc = (in_pos / u_screen) * 2.0 - 1.0;\n"
        "    ndc.y = -ndc.y;\n"
        "    gl_Position = vec4(ndc, 0.0, 1.0);\n"
        "}\n"
    )
    fs = (
        "#version 330\n"
        "uniform vec4 u_color;\n"
        "out vec4 f_color;\n"
        "void main() {\n"
        "    f_color = u_color;\n"
        "}\n"
    )
    return ctx.program(vertex_shader=vs, fragment_shader=fs)


def _draw_lines(ctx, line_prog, vertices, screen_w, screen_h, color, width=1.0):
    if not vertices:
        return
    arr = np.array(vertices, dtype="f4")
    vbo = ctx.buffer(arr.tobytes())
    vao = ctx.vertex_array(line_prog, [(vbo, "2f", "in_pos")])
    line_prog["u_screen"].value = (float(screen_w), float(screen_h))
    line_prog["u_color"].value = tuple(float(c) for c in color)
    # Some drivers/core profiles only support line width = 1.0.
    # Writing unsupported widths can raise GL_INVALID_VALUE and break imgui render.
    _ = width
    vao.render(moderngl.LINES)
    vao.release()
    vbo.release()


def _draw_rect_outline(ctx, line_prog, x, y, w, h, screen_w, screen_h, color, width=1.0):
    x0 = float(x)
    y0 = float(y)
    x1 = float(x + w)
    y1 = float(y + h)
    verts = [
        x0, y0, x1, y0,
        x1, y0, x1, y1,
        x1, y1, x0, y1,
        x0, y1, x0, y0,
    ]
    _draw_lines(ctx, line_prog, verts, screen_w, screen_h, color, width)


class PortraitTextureCache:
    """缓存处理过的立绘纹理，避免每帧重复 PIL 处理"""

    def __init__(self, ctx):
        self.ctx = ctx
        self._cache = {}
        self._textures = {}  # tex_id -> tex object

    def _make_key(self, char_name, portrait_key, sentence_scale, sat, alpha):
        return (
            char_name,
            portrait_key,
            int(sentence_scale * 1000),
            int(sat * 1000),
            int(alpha * 1000),
        )

    def get(self, char_name, char_cfg, portrait_key, sentence_scale, saturation, alpha):
        if not isinstance(char_cfg, dict):
            return None, (0.5, 0.95)

        key = self._make_key(
            char_name,
            portrait_key,
            sentence_scale,
            saturation,
            alpha,
        )
        if key in self._cache:
            return self._cache[key]

        src_img, pinfo, anchor = _load_portrait_surface(char_cfg, portrait_key)
        if src_img is None:
            return None, (0.5, 0.95)

        sentence_scale = float(sentence_scale or 1.0)
        base_scale = char_cfg.get("base_scale", 1.0)
        ps_scale = float(pinfo.get("scale", 1.0) or 1.0)
        final_scale = max(0.01, sentence_scale * base_scale * ps_scale)
        scaled_w = max(1, int(src_img.width * final_scale))
        scaled_h = max(1, int(src_img.height * final_scale))
        processed = _apply_effects(src_img, saturation, alpha, (scaled_w, scaled_h))
        tex = _pil_to_mgl_texture(self.ctx, processed)
        self._cache[key] = (tex, anchor)
        self._textures[id(tex)] = tex
        return tex, anchor

    def clear(self):
        for tex in self._textures.values():
            tex.release()
        self._cache.clear()
        self._textures.clear()


def run_editor():
    if not glfw.init():
        raise RuntimeError("glfw.init failed")

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.RESIZABLE, True)

    window = glfw.create_window(EDITOR_W, EDITOR_H, "立绘编辑器", None, None)
    if not window:
        glfw.terminate()
        raise RuntimeError("glfw.create_window failed")

    glfw.make_context_current(window)
    ctx = moderngl.create_context()
    ctx.enable(moderngl.BLEND)
    ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

    # ---- FBO for game-resolution preview ----
    preview_tex = ctx.texture((GAME_VIEW_W, GAME_VIEW_H), 4)
    preview_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
    fbo = ctx.framebuffer(preview_tex)

    # ---- Programs ----
    blit_prog, blit_vao = _create_blit_program(ctx)
    portrait_prog = _create_portrait_program(ctx)
    line_prog = _create_color_line_program(ctx)

    # ---- Texture cache ----
    tex_cache = PortraitTextureCache(ctx)

    # ---- imgui setup ----
    imgui.create_context()
    io = imgui.get_io()
    font_path = os.path.join(root, "assets", "fonts", "SourceHanSansCN-Bold.otf")
    if not os.path.exists(font_path):
        font_path = os.path.join(root, "assets", "fonts", "wqy-microhei-mono.ttf")
    if os.path.exists(font_path):
        io.fonts.clear()
        io.fonts.add_font_from_file_ttf(font_path, 16, glyph_ranges=io.fonts.get_glyph_ranges_chinese_full())

    impl = create_glfw_renderer(window)
    if os.path.exists(font_path):
        impl.refresh_font_texture()

    # ---- State ----
    layout = load_layout()
    characters = load_characters()

    char_names = list(characters.keys())
    left_char_idx = 0 if char_names else -1
    right_char_idx = 1 if len(char_names) > 1 else 0 if char_names else -1

    left_portrait_key = "Happy"
    right_portrait_key = "Happy"
    active_position = "left"  # "left" or "right"
    preview_scale = 1.0

    def _selected_char_name(index):
        return char_names[index] if 0 <= index < len(char_names) else ""

    def _get_char_base_scale(char_name):
        cfg = characters.get(char_name)
        if not isinstance(cfg, dict):
            return 1.0
        return float(cfg.get("base_scale", 1.0) or 1.0)

    def _set_char_base_scale(char_name, value):
        cfg = characters.get(char_name)
        if not isinstance(cfg, dict):
            return 1.0
        clamped = max(0.01, min(4.0, float(value)))
        cfg["base_scale"] = round(clamped, 3)
        return cfg["base_scale"]

    def _save_character_config(char_name):
        if not char_name:
            return False, "未选择角色"
        cfg = characters.get(char_name)
        if not isinstance(cfg, dict):
            return False, f"找不到角色配置: {char_name}"

        cfg_path = os.path.join(CHAR_DIR, char_name, "character.json")
        if not os.path.exists(cfg_path):
            source_folder = cfg.get("__source_folder")
            if source_folder:
                cfg_path = os.path.join(CHAR_DIR, str(source_folder), "character.json")

        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
                f.write("\n")
            return True, f"已保存角色缩放: {char_name}"
        except Exception as exc:
            return False, f"保存角色失败: {char_name} ({exc})"

    left_char_scale = _get_char_base_scale(_selected_char_name(left_char_idx))
    right_char_scale = _get_char_base_scale(_selected_char_name(right_char_idx))

    # drag state
    dragging_slot = None  # "left" | "right" | None
    drag_start_mouse = None

    status_msg = ""
    status_frames = 0

    def render_preview():
        fbo.use()
        ctx.viewport = (0, 0, GAME_VIEW_W, GAME_VIEW_H)
        ctx.clear(0.05, 0.05, 0.12)

        focus = layout.get("focus", {})
        sp_lift = focus.get("speaker_lift_px", 20)
        ip_lift = focus.get("inactive_lift_px", 0)
        act_sat = focus.get("active_saturation", 1.0)
        inact_sat = focus.get("inactive_saturation", 0.35)
        act_alpha = focus.get("active_alpha", 1.0)
        inact_alpha = focus.get("inactive_alpha", 0.62)

        # Load character configs for left/right
        left_char_name = char_names[left_char_idx] if 0 <= left_char_idx < len(char_names) else ""
        right_char_name = char_names[right_char_idx] if 0 <= right_char_idx < len(char_names) else ""
        left_char = characters[left_char_name] if left_char_name in characters else None
        right_char = characters[right_char_name] if right_char_name in characters else None

        # Determine effective portrait keys
        lpk = left_portrait_key
        rpk = right_portrait_key
        if left_char and lpk not in left_char.get("portraits", {}):
            lpk = left_char.get("default_portrait", "Happy")
        if right_char and rpk not in right_char.get("portraits", {}):
            rpk = right_char.get("default_portrait", "Happy")

        slots = layout.get("slots", {})
        left_anchor = slots.get("left", {}).get("anchor_px", [220, GAME_VIEW_H - 40])
        right_anchor = slots.get("right", {}).get("anchor_px", [GAME_VIEW_W - 220, GAME_VIEW_H - 40])

        render_order = layout.get("render_order", ["left", "right"])
        for slot_name in render_order:
            is_left = slot_name == "left"
            is_active = (is_left and active_position == "left") or (not is_left and active_position == "right")

            char_cfg = left_char if is_left else right_char
            char_name = left_char_name if is_left else right_char_name
            port_key = lpk if is_left else rpk
            anchor_px = left_anchor if is_left else right_anchor

            sat = act_sat if is_active else inact_sat
            alpha = act_alpha if is_active else inact_alpha
            lift = sp_lift if is_active else ip_lift

            tex, char_anchor = tex_cache.get(char_name, char_cfg, port_key, preview_scale, sat, alpha)
            if tex is None:
                continue

            aw, ah = char_anchor
            ax = anchor_px[0]
            ay = anchor_px[1] - lift  # lift goes UP (subtract from Y)

            # Build quad vertices (in pixels, relative to anchor)
            tex_w, tex_h = tex.width, tex.height
            vertices = np.array([
                -aw * tex_w, -ah * tex_h, 0.0, 0.0,
                -aw * tex_w, (1 - ah) * tex_h, 0.0, 1.0,
                (1 - aw) * tex_w, -ah * tex_h, 1.0, 0.0,
                (1 - aw) * tex_w, -ah * tex_h, 1.0, 0.0,
                -aw * tex_w, (1 - ah) * tex_h, 0.0, 1.0,
                (1 - aw) * tex_w, (1 - ah) * tex_h, 1.0, 1.0,
            ], dtype='f4')
            quad_vbo = ctx.buffer(vertices.tobytes())
            quad_vao = ctx.vertex_array(portrait_prog, [(quad_vbo, '2f 2f', 'in_pos', 'in_uv')])

            portrait_prog['u_anchor'].value = (ax, ay)
            portrait_prog['u_screen'].value = (float(GAME_VIEW_W), float(GAME_VIEW_H))
            tex.use(0)
            portrait_prog['u_tex'].value = 0
            quad_vao.render(moderngl.TRIANGLES)

            quad_vbo.release()
            quad_vao.release()

        # Draw crosshair markers for anchors
        _draw_crosshair(ctx, line_prog, left_anchor[0], left_anchor[1], GAME_VIEW_W, GAME_VIEW_H, (0.42, 0.77, 1.0, 1.0))
        _draw_crosshair(ctx, line_prog, right_anchor[0], right_anchor[1], GAME_VIEW_W, GAME_VIEW_H, (1.0, 0.64, 0.47, 1.0))

    def blit_preview(x, y, w, h):
        ctx.screen.use()
        ctx.viewport = (x, y, w, h)
        preview_tex.use(0)
        blit_prog['u_tex'].value = 0
        blit_vao.render(moderngl.TRIANGLES)

    def _draw_crosshair(ctx, line_program, px, py, sw, sh, color):
        """在像素位置 (px, py) 绘制十字丝。"""
        size = 12.0
        verts = [
            float(px - size), float(py), float(px + size), float(py),
            float(px), float(py - size), float(px), float(py + size),
        ]
        _draw_lines(ctx, line_program, verts, sw, sh, color, width=2.0)

    # ---- Mouse state for drag ----
    mouse_in_preview = False
    preview_rect = [0, 0, 0, 0]  # x, y, w, h in screen coords

    while not glfw.window_should_close(window):
        glfw.poll_events()
        frame_begin(impl)

        # Render preview to FBO
        render_preview()

        # Switch to default framebuffer
        ctx.screen.use()
        fw, fh = glfw.get_framebuffer_size(window)
        ctx.viewport = (0, 0, fw, fh)
        ctx.clear(0.12, 0.13, 0.16)

        # Blit preview to right side (letterboxed to match game viewport aspect ratio)
        preview_x = PANEL_W
        preview_y = 0
        preview_w = max(1, fw - PANEL_W)
        preview_h = fh
        # Compute letterboxed inner rect
        avail_w = preview_w
        avail_h = preview_h
        scale = min(avail_w / GAME_VIEW_W, avail_h / GAME_VIEW_H)
        inner_w = int(GAME_VIEW_W * scale)
        inner_h = int(GAME_VIEW_H * scale)
        inner_x = preview_x + (avail_w - inner_w) // 2
        inner_y = preview_y + (avail_h - inner_h) // 2
        blit_preview(inner_x, inner_y, inner_w, inner_h)
        # Overlay lines are in screen coordinates, so restore full-screen viewport first.
        ctx.viewport = (0, 0, fw, fh)
        _draw_rect_outline(ctx, line_prog, inner_x, inner_y, inner_w, inner_h, fw, fh, (0.72, 0.86, 1.0, 0.95), width=1.0)
        preview_rect = [inner_x, inner_y, inner_w, inner_h]

        # ---- imgui panel ----
        imgui.set_next_window_position(0.0, 0.0)
        imgui.set_next_window_size(float(PANEL_W), float(fh))
        imgui.begin("立绘编辑器", flags=imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_COLLAPSE)

        changed = False

        # --- Toolbar ---
        if imgui.button("保存布局"):
            save_layout(layout)
            status_msg = "已保存"
            status_frames = 180
        imgui.same_line()
        if imgui.button("加载"):
            layout = load_layout()
            status_msg = "已加载"
            status_frames = 180
        imgui.same_line()
        if imgui.button("重置"):
            layout = default_layout()
            status_msg = "已重置"
            status_frames = 180
        imgui.separator()

        # --- Character / Expression Selection ---
        imgui.text("角色选择")
        imgui.separator()

        imgui.text("左立绘")
        left_changed, left_char_idx = imgui.combo("##left_char", left_char_idx, char_names) if char_names else (False, 0)
        if left_changed:
            left_char_scale = _get_char_base_scale(_selected_char_name(left_char_idx))
        if char_names and 0 <= left_char_idx < len(char_names):
            left_char_cfg = characters[char_names[left_char_idx]]
            left_portrait_keys = list(left_char_cfg.get("portraits", {}).keys())
            if not left_portrait_keys:
                left_portrait_keys = ["normal"]
            if left_portrait_key not in left_portrait_keys:
                left_portrait_key = left_portrait_keys[0]
            left_portrait_idx = left_portrait_keys.index(left_portrait_key)
            _, left_portrait_idx = imgui.combo("表情##left", left_portrait_idx, left_portrait_keys)
            left_portrait_key = left_portrait_keys[left_portrait_idx]

        imgui.text("右立绘")
        right_changed, right_char_idx = imgui.combo("##right_char", right_char_idx, char_names) if char_names else (False, 0)
        if right_changed:
            right_char_scale = _get_char_base_scale(_selected_char_name(right_char_idx))
        if char_names and 0 <= right_char_idx < len(char_names):
            right_char_cfg = characters[char_names[right_char_idx]]
            right_portrait_keys = list(right_char_cfg.get("portraits", {}).keys())
            if not right_portrait_keys:
                right_portrait_keys = ["normal"]
            if right_portrait_key not in right_portrait_keys:
                right_portrait_key = right_portrait_keys[0]
            right_portrait_idx = right_portrait_keys.index(right_portrait_key)
            _, right_portrait_idx = imgui.combo("表情##right", right_portrait_idx, right_portrait_keys)
            right_portrait_key = right_portrait_keys[right_portrait_idx]

        imgui.separator()
        imgui.text("角色独立缩放")
        imgui.separator()

        current_left_name = _selected_char_name(left_char_idx)
        current_right_name = _selected_char_name(right_char_idx)

        if current_left_name:
            imgui.text(f"左角色: {current_left_name}")
            left_scale_changed, left_char_scale = imgui.slider_float(
                "Base Scale##left_char_scale", left_char_scale, 0.01, 3.0
            )
            if left_scale_changed:
                left_char_scale = _set_char_base_scale(current_left_name, left_char_scale)
                if current_right_name == current_left_name:
                    right_char_scale = left_char_scale
                tex_cache.clear()
        else:
            imgui.text("左角色: 未选择")

        if current_right_name:
            imgui.text(f"右角色: {current_right_name}")
            right_scale_changed, right_char_scale = imgui.slider_float(
                "Base Scale##right_char_scale", right_char_scale, 0.01, 3.0
            )
            if right_scale_changed:
                right_char_scale = _set_char_base_scale(current_right_name, right_char_scale)
                if current_left_name == current_right_name:
                    left_char_scale = right_char_scale
                tex_cache.clear()
        else:
            imgui.text("右角色: 未选择")

        if imgui.button("保存左角色缩放"):
            ok, msg = _save_character_config(current_left_name)
            status_msg = msg
            status_frames = 240 if ok else 360
        imgui.same_line()
        if imgui.button("保存右角色缩放"):
            ok, msg = _save_character_config(current_right_name)
            status_msg = msg
            status_frames = 240 if ok else 360

        imgui.separator()
        imgui.text("焦点效果")
        imgui.separator()

        focus = layout.setdefault("focus", {})

        _, val = imgui.slider_int("说话者上移 px", int(focus.get("speaker_lift_px", 20)), 0, 120)
        focus["speaker_lift_px"] = val

        _, val = imgui.slider_int("非说话者上移 px", int(focus.get("inactive_lift_px", 0)), 0, 120)
        focus["inactive_lift_px"] = val

        _, val = imgui.slider_float("Active Alpha", float(focus.get("active_alpha", 1.0)), 0.1, 1.0)
        focus["active_alpha"] = round(val, 3)

        _, val = imgui.slider_float("Inactive Alpha", float(focus.get("inactive_alpha", 0.62)), 0.1, 1.0)
        focus["inactive_alpha"] = round(val, 3)

        _, val = imgui.slider_float("Active Saturation", float(focus.get("active_saturation", 1.0)), 0.0, 1.5)
        focus["active_saturation"] = round(val, 3)

        _, val = imgui.slider_float("Inactive Saturation", float(focus.get("inactive_saturation", 0.35)), 0.0, 1.5)
        focus["inactive_saturation"] = round(val, 3)

        imgui.separator()
        imgui.text("锚点位置")
        imgui.separator()

        slots = layout.setdefault("slots", {})

        _, val = imgui.slider_int("左 Anchor X", int(slots.get("left", {}).get("anchor_px", [220, GAME_VIEW_H - 40])[0]), 0, GAME_VIEW_W)
        slots.setdefault("left", {})["anchor_px"][0] = val

        _, val = imgui.slider_int("左 Anchor Y", int(slots.get("left", {}).get("anchor_px", [220, GAME_VIEW_H - 40])[1]), 0, GAME_VIEW_H)
        slots.setdefault("left", {})["anchor_px"][1] = val

        _, val = imgui.slider_int("右 Anchor X", int(slots.get("right", {}).get("anchor_px", [GAME_VIEW_W - 220, GAME_VIEW_H - 40])[0]), 0, GAME_VIEW_W)
        slots.setdefault("right", {})["anchor_px"][0] = val

        _, val = imgui.slider_int("右 Anchor Y", int(slots.get("right", {}).get("anchor_px", [GAME_VIEW_W - 220, GAME_VIEW_H - 40])[1]), 0, GAME_VIEW_H)
        slots.setdefault("right", {})["anchor_px"][1] = val

        imgui.separator()
        imgui.text("预览缩放")
        _, preview_scale = imgui.slider_float("Scale", preview_scale, 0.2, 2.0)
        imgui.text("说明: Scale 仅用于临时预览，不会保存到角色配置")
        imgui.text(f"游戏视口: {GAME_VIEW_W}x{GAME_VIEW_H}")

        imgui.separator()
        imgui.text("说话者")
        if imgui.radio_button("左侧", active_position == "left"):
            active_position = "left"
        imgui.same_line()
        if imgui.radio_button("右侧", active_position == "right"):
            active_position = "right"

        imgui.separator()
        imgui.text("快捷键")
        imgui.text("A: 左侧说话  D: 右侧说话")
        imgui.text("S: 保存  ESC: 退出")
        imgui.text("提示: 可在右侧预览区拖拽锚点")

        if status_frames > 0:
            status_frames -= 1
            imgui.text_colored(status_msg, 0.4, 1.0, 0.6, 1.0)

        imgui.end()

        # ---- Keyboard shortcuts ----
        # These need to be handled via glfw directly since imgui captures keys
        # We'll check via imgui's io which keys are pressed this frame
        io = imgui.get_io()
        if io.keys_down[ord('a')] or io.keys_down[ord('A')]:
            active_position = "left"
            io.keys_down[ord('a')] = False
            io.keys_down[ord('A')] = False
        if io.keys_down[ord('d')] or io.keys_down[ord('D')]:
            active_position = "right"
            io.keys_down[ord('d')] = False
            io.keys_down[ord('D')] = False
        if io.keys_down[ord('s')] or io.keys_down[ord('S')]:
            save_layout(layout)
            status_msg = "已保存"
            status_frames = 180
            io.keys_down[ord('s')] = False
            io.keys_down[ord('S')] = False

        # ---- Mouse drag for anchors ----
        # We need to detect when mouse is pressed INSIDE the preview area
        # but OUTSIDE any imgui window
        mx, my = glfw.get_cursor_pos(window)
        # Convert window coords to framebuffer coords (HiDPI-safe)
        win_w, win_h = glfw.get_window_size(window)
        scale_x = fw / max(1.0, float(win_w))
        scale_y = fh / max(1.0, float(win_h))
        mx_fb = mx * scale_x
        my_fb = my * scale_y

        # Check if mouse is in preview area
        in_prev = (preview_rect[0] <= mx_fb < preview_rect[0] + preview_rect[2] and
               preview_rect[1] <= my_fb < preview_rect[1] + preview_rect[3])

        # Get mouse button state from glfw
        mouse_pressed = glfw.get_mouse_button(window, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS

        if mouse_pressed and in_prev:
            # Convert framebuffer coords to game-view coords.
            prev_local_x = (mx_fb - preview_rect[0]) / max(1.0, preview_rect[2]) * GAME_VIEW_W
            prev_local_y = (my_fb - preview_rect[1]) / max(1.0, preview_rect[3]) * GAME_VIEW_H
            prev_local_x = max(0.0, min(GAME_VIEW_W - 1.0, prev_local_x))
            prev_local_y = max(0.0, min(GAME_VIEW_H - 1.0, prev_local_y))
            # Dialog layout y-axis is top-down in viewport coordinates.
            game_y = prev_local_y

            slots = layout.setdefault("slots", {})
            left_anchor = slots.setdefault("left", {})["anchor_px"]
            right_anchor = slots.setdefault("right", {})["anchor_px"]

            if dragging_slot is None:
                # Determine which anchor is closer
                dist_l = ((prev_local_x - left_anchor[0]) ** 2 + (game_y - left_anchor[1]) ** 2) ** 0.5
                dist_r = ((prev_local_x - right_anchor[0]) ** 2 + (game_y - right_anchor[1]) ** 2) ** 0.5
                threshold = 60  # pixels in game coords
                if dist_l < dist_r and dist_l < threshold:
                    dragging_slot = "left"
                elif dist_r < threshold:
                    dragging_slot = "right"

            if dragging_slot:
                if dragging_slot == "left":
                    left_anchor[0] = max(0, min(GAME_VIEW_W, int(prev_local_x)))
                    left_anchor[1] = max(0, min(GAME_VIEW_H, int(game_y)))
                else:
                    right_anchor[0] = max(0, min(GAME_VIEW_W, int(prev_local_x)))
                    right_anchor[1] = max(0, min(GAME_VIEW_H, int(game_y)))
        else:
            dragging_slot = None

        frame_end(impl)
        glfw.swap_buffers(window)

    impl.shutdown()
    tex_cache.clear()
    portrait_prog.release()
    line_prog.release()
    fbo.release()
    preview_tex.release()
    blit_vao.release()
    blit_prog.release()
    glfw.destroy_window(window)
    glfw.terminate()
