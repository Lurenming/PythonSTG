"""
ModernGL 对话渲染器

使用 FontRenderer 渲染中文文本到 SoftwareSurface，
然后上传为 GL 纹理并绘制 textured quad。

支持:
- 中文文本（通过 TrueType 字体）
- 半透明背景
- 角色名显示
- 打字机效果
- 自动换行
- [按 Z 继续] 提示
"""

import json
import moderngl
import numpy as np
import os
from typing import Dict, Tuple, Optional, Any
from PIL import ImageEnhance

from ..core.image_loader import SoftwareSurface, FontRenderer, load_image_surface


class DialogGLRenderer:
    """基于 ModernGL 的对话框渲染器"""

    def __init__(self, ctx: moderngl.Context, screen_width: int, screen_height: int, game_viewport: tuple):
        """
        Args:
            ctx: ModernGL 上下文
            screen_width: 窗口宽度（像素）
            screen_height: 窗口高度（像素）
            game_viewport: 游戏区域 (x, y, width, height)
        """
        self.ctx = ctx
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.game_viewport = game_viewport

        # 对话框尺寸（窗口像素坐标）
        gx, gy, gw, gh = game_viewport
        self.box_margin = 20
        self.box_width = gw - self.box_margin * 2
        self.box_height = 180
        self.box_x = gx + self.box_margin
        self.box_y = gy + gh - self.box_height - self.box_margin
        self._quad_rect = (self.box_x, self.box_y, self.box_width, self.box_height)

        # Default balloon positions in game viewport coordinates
        self._balloon_default_left = (280, 880)
        self._balloon_default_right = (880, 880)

        # 加载中文字体
        font_path = os.path.join("assets", "fonts", "SourceHanSansCN-Bold.otf")
        if not os.path.exists(font_path):
            font_path = os.path.join("assets", "fonts", "wqy-microhei-mono.ttf")
        if not os.path.exists(font_path):
            font_path = None

        self.font = FontRenderer(font_path, 28)
        self.name_font = FontRenderer(font_path, 22)
        self.balloon_font = FontRenderer(font_path, 24)
        self.balloon_hint_font = FontRenderer(font_path, 18)

        # Balloon assets
        self._balloon_config = None
        self._balloon_sprites = {}
        self._load_balloon_assets()

        # Character portrait assets
        self._character_portraits = {}  # {"CharName/portrait": SoftwareSurface}
        self._portrait_configs = {}      # {"CharName": config dict}
        self._portrait_layout = self._load_portrait_layout()
        self._portrait_effect_cache: Dict[Tuple[Any, ...], SoftwareSurface] = {}
        self._load_character_portraits()

        # GL 资源
        self._init_shader()
        self._dialog_texture = None
        self._portrait_texture = None

    def _load_portrait_layout(self) -> Dict[str, Any]:
        gx, gy, gw, gh = self.game_viewport
        default_layout = {
            "slots": {
                "left": {"anchor_px": [220, gh - 40]},
                "right": {"anchor_px": [gw - 220, gh - 40]},
            },
            "focus": {
                "speaker_lift_px": 20,
                "active_alpha": 1.0,
                "inactive_alpha": 0.62,
                "active_saturation": 1.0,
                "inactive_saturation": 0.35,
            },
            "render_order": ["left", "right"],
        }
        config_path = os.path.join("assets", "ui", "dialog_portrait_layout.json")
        if not os.path.exists(config_path):
            return default_layout
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if not isinstance(loaded, dict):
                return default_layout
            merged = default_layout
            merged["slots"].update(loaded.get("slots", {}))
            merged["focus"].update(loaded.get("focus", {}))
            render_order = loaded.get("render_order")
            if isinstance(render_order, list) and render_order:
                merged["render_order"] = render_order
            return merged
        except Exception:
            return default_layout

    def _init_shader(self):
        """初始化 textured quad 着色器"""
        vertex_shader = """
        #version 330

        uniform vec2 u_screen_size;

        in vec2 in_position;
        in vec2 in_uv;

        out vec2 v_uv;

        void main() {
            vec2 ndc = (in_position / u_screen_size) * 2.0 - 1.0;
            ndc.y = -ndc.y;
            gl_Position = vec4(ndc, 0.0, 1.0);
            v_uv = in_uv;
        }
        """

        fragment_shader = """
        #version 330

        uniform sampler2D u_texture;

        in vec2 v_uv;

        out vec4 f_color;

        void main() {
            f_color = texture(u_texture, v_uv);
        }
        """

        self.program = self.ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader
        )
        self.program['u_texture'].value = 0
        self.program['u_screen_size'].value = (float(self.screen_width), float(self.screen_height))

        # 顶点缓冲区（6 vertices * 4 floats * 4 bytes）
        self.vbo = self.ctx.buffer(reserve=6 * 4 * 4)
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, '2f 2f', 'in_position', 'in_uv')]
        )

    def render(self, dialog_state):
        """
        渲染对话框

        Args:
            dialog_state: SimpleDialogTextRenderer 实例，
                         包含 current_sentence 和 visible_chars 属性
        """
        if dialog_state is None:
            return
        if not hasattr(dialog_state, 'current_sentence') or dialog_state.current_sentence is None:
            return

        sentence = dialog_state.current_sentence

        # 先渲染立绘（在气泡下层）
        self._render_portraits(dialog_state)

        # Render to SoftwareSurface
        surface, quad_rect = self._render_to_surface(dialog_state)
        if surface is None:
            return

        self._quad_rect = quad_rect

        # 上传为 GL 纹理
        self._upload_texture(surface)

        # 绘制 quad
        self._draw_quad()

    def _render_to_surface(self, dialog_state):
        """Render dialog content to SoftwareSurface."""
        sentence = dialog_state.current_sentence
        if sentence is None:
            return None, self._quad_rect

        if self._balloon_config and self._balloon_sprites:
            return self._render_balloon_surface(sentence, dialog_state.visible_chars, dialog_state.frame_counter)

        # Fallback: dialog box
        surface = SoftwareSurface(self.box_width, self.box_height)
        surface.fill((0, 0, 0, 180))

        if sentence.character:
            name_surface = self.name_font.render(sentence.character, True, (255, 255, 100))
            surface.blit(name_surface, (15, 10))

        visible_text = sentence.text[:dialog_state.visible_chars]
        lines = self._wrap_text(visible_text, self.font, self.box_width - 30)
        y = 45
        for line in lines:
            text_surface = self.font.render(line, True, (255, 255, 255))
            surface.blit(text_surface, (15, y))
            y += 35

        return surface, (self.box_x, self.box_y, self.box_width, self.box_height)

    def _wrap_text(self, text, font, max_width):
        """逐字换行"""
        lines = []
        current_line = ""
        for char in text:
            test_line = current_line + char
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
        return lines

    def _upload_texture(self, surface):
        """将 SoftwareSurface 上传为 ModernGL 纹理"""
        data = surface.to_bytes("RGBA", flip_y=True)
        w, h = surface.get_size()

        if self._dialog_texture is not None:
            if self._dialog_texture.size == (w, h):
                self._dialog_texture.write(data)
            else:
                self._dialog_texture.release()
                self._dialog_texture = self.ctx.texture((w, h), 4, data)
                self._dialog_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        else:
            self._dialog_texture = self.ctx.texture((w, h), 4, data)
            self._dialog_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)

    def _draw_quad(self):
        """绘制对话框 quad"""
        if self._dialog_texture is None:
            return

        x, y, w, h = self._quad_rect
        x0 = float(x)
        y0 = float(y)
        x1 = float(x + w)
        y1 = float(y + h)

        # tobytes(flip=True)：v=0 对应 Surface 底部，v=1 对应 Surface 顶部
        vertices = np.array([
            # 三角形 1
            x0, y0, 0.0, 1.0,   # 左上 → 纹理顶部
            x0, y1, 0.0, 0.0,   # 左下 → 纹理底部
            x1, y0, 1.0, 1.0,   # 右上 → 纹理顶部
            # 三角形 2
            x1, y0, 1.0, 1.0,   # 右上
            x0, y1, 0.0, 0.0,   # 左下
            x1, y1, 1.0, 0.0,   # 右下 → 纹理底部
        ], dtype='f4')

        self.vbo.write(vertices.tobytes())
        self._dialog_texture.use(0)
        self.vao.render(moderngl.TRIANGLES)

    def _render_portraits(self, dialog_state):
        """渲染角色立绘（支持左右双人同屏）"""
        sentence = getattr(dialog_state, "current_sentence", None)
        if not sentence:
            return

        slots = {}
        state_slots = getattr(dialog_state, "portrait_slots", None)
        if isinstance(state_slots, dict):
            for pos in ("left", "right"):
                slot_entry = state_slots.get(pos)
                if isinstance(slot_entry, dict) and slot_entry.get("character"):
                    slots[pos] = slot_entry

        if not slots and getattr(sentence, "character", None):
            pos = getattr(sentence, "position", "left")
            if pos not in ("left", "right"):
                pos = "left"
            slots[pos] = {
                "character": sentence.character,
                "portrait": getattr(sentence, "portrait", "normal") or "normal",
                "position": pos,
                "portrait_scale": getattr(sentence, "portrait_scale", 1.0),
                "portrait_x": getattr(sentence, "portrait_x", None),
                "portrait_y": getattr(sentence, "portrait_y", None),
            }

        active_pos = getattr(dialog_state, "active_speaker_position", None)
        if active_pos not in ("left", "right"):
            active_pos = getattr(sentence, "position", "left")
        if active_pos not in ("left", "right"):
            active_pos = "left"

        render_order = self._portrait_layout.get("render_order", ["left", "right"])
        for pos in render_order:
            if pos not in ("left", "right"):
                continue
            slot_entry = slots.get(pos)
            if slot_entry:
                self._render_portrait_slot(slot_entry, pos, is_active=(pos == active_pos))

    def _render_portrait_slot(self, slot_entry: Dict[str, Any], position: str, is_active: bool):
        char_name = slot_entry.get("character")
        if not char_name:
            return

        config = self._portrait_configs.get(char_name, {})
        requested_key = slot_entry.get("portrait", "normal") or "normal"
        portrait_id = f"{char_name}/{requested_key}"
        portrait_surface = self._character_portraits.get(portrait_id)
        portrait_info = config.get("portraits", {}).get(requested_key, {})
        if not portrait_surface:
            default_key = config.get("default_portrait", "normal")
            portrait_id = f"{char_name}/{default_key}"
            portrait_surface = self._character_portraits.get(portrait_id)
            portrait_info = config.get("portraits", {}).get(default_key, {})
            if not portrait_surface:
                return

        sentence_scale = float(slot_entry.get("portrait_scale", 1.0) or 1.0)
        base_scale = float(config.get("base_scale", 1.0) or 1.0)
        portrait_scale = float(portrait_info.get("scale", 1.0) or 1.0)
        final_scale = max(0.01, sentence_scale * base_scale * portrait_scale)

        src_w, src_h = portrait_surface.get_size()
        target_w = max(1, int(src_w * final_scale))
        target_h = max(1, int(src_h * final_scale))

        focus_cfg = self._portrait_layout.get("focus", {})
        if is_active:
            alpha = self._clamp01(float(focus_cfg.get("active_alpha", 1.0)))
            saturation = max(0.0, float(focus_cfg.get("active_saturation", 1.0)))
            lift_px = int(focus_cfg.get("speaker_lift_px", 0))
        else:
            alpha = self._clamp01(float(focus_cfg.get("inactive_alpha", 0.62)))
            saturation = max(0.0, float(focus_cfg.get("inactive_saturation", 0.35)))
            lift_px = int(focus_cfg.get("inactive_lift_px", 0))

        processed = self._prepare_portrait_surface(
            portrait_id=portrait_id,
            base_surface=portrait_surface,
            target_size=(target_w, target_h),
            saturation=saturation,
            alpha=alpha,
        )
        pw, ph = processed.get_size()

        px_override = slot_entry.get("portrait_x")
        py_override = slot_entry.get("portrait_y")
        if px_override is not None and py_override is not None:
            px = int(px_override)
            py = int(py_override) - lift_px
        else:
            slot_anchor = self._resolve_slot_anchor(position, config)
            ax, ay = self._resolve_anchor_ratio(portrait_info, src_w, src_h)
            px = int(slot_anchor[0] - ax * pw)
            py = int(slot_anchor[1] - ay * ph - lift_px)

        self._draw_portrait_surface(processed, px, py)

    def _resolve_slot_anchor(self, position: str, config: Dict[str, Any]) -> Tuple[int, int]:
        gx, gy, gw, gh = self.game_viewport
        slots_cfg = self._portrait_layout.get("slots", {})
        slot_cfg = slots_cfg.get(position, {})
        anchor_px = slot_cfg.get("anchor_px", [220 if position == "left" else gw - 220, gh - 40])
        if not isinstance(anchor_px, (list, tuple)) or len(anchor_px) < 2:
            anchor_px = [220 if position == "left" else gw - 220, gh - 40]
        x = int(anchor_px[0])
        y = int(anchor_px[1])

        slot_offset_cfg = config.get("slot_offset", {})
        if isinstance(slot_offset_cfg, dict):
            offset = slot_offset_cfg.get(position, [0, 0])
        else:
            offset = [0, 0]
        if isinstance(offset, (list, tuple)) and len(offset) >= 2:
            x += int(offset[0])
            y += int(offset[1])

        return gx + x, gy + y

    def _resolve_anchor_ratio(self, portrait_info: Dict[str, Any], width: int, height: int) -> Tuple[float, float]:
        anchor = portrait_info.get("anchor")
        if anchor is None:
            anchor = portrait_info.get("center", [0.5, 0.95])
        if not isinstance(anchor, (list, tuple)) or len(anchor) < 2:
            return 0.5, 0.95
        ax = float(anchor[0])
        ay = float(anchor[1])
        if ax > 1.0:
            ax = ax / max(1.0, float(width))
        if ay > 1.0:
            ay = ay / max(1.0, float(height))
        return self._clamp01(ax), self._clamp01(ay)

    def _prepare_portrait_surface(
        self,
        portrait_id: str,
        base_surface: SoftwareSurface,
        target_size: Tuple[int, int],
        saturation: float,
        alpha: float,
    ) -> SoftwareSurface:
        cache_key = (
            portrait_id,
            target_size[0],
            target_size[1],
            int(saturation * 1000),
            int(alpha * 1000),
        )
        cached = self._portrait_effect_cache.get(cache_key)
        if cached is not None:
            return cached

        src_w, src_h = base_surface.get_size()
        if (src_w, src_h) == target_size:
            surface = base_surface
        else:
            surface = SoftwareSurface.smoothscale(base_surface, target_size)

        needs_effect = abs(saturation - 1.0) > 1e-4 or abs(alpha - 1.0) > 1e-4
        if needs_effect:
            img = surface._image.copy()
            if abs(saturation - 1.0) > 1e-4:
                img = ImageEnhance.Color(img).enhance(saturation)
            if abs(alpha - 1.0) > 1e-4:
                alpha_band = img.split()[3]
                alpha_band = alpha_band.point(lambda p: int(max(0, min(255, p * alpha))))
                img.putalpha(alpha_band)
            surface = SoftwareSurface(img)

        if len(self._portrait_effect_cache) > 256:
            self._portrait_effect_cache.clear()
        self._portrait_effect_cache[cache_key] = surface
        return surface

    def _draw_portrait_surface(self, portrait_surface: SoftwareSurface, px: int, py: int):
        pw, ph = portrait_surface.get_size()
        data = portrait_surface.to_bytes("RGBA", flip_y=True)
        if self._portrait_texture is not None:
            if self._portrait_texture.size == (pw, ph):
                self._portrait_texture.write(data)
            else:
                self._portrait_texture.release()
                self._portrait_texture = self.ctx.texture((pw, ph), 4, data)
                self._portrait_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        else:
            self._portrait_texture = self.ctx.texture((pw, ph), 4, data)
            self._portrait_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)

        x0 = float(px)
        y0 = float(py)
        x1 = float(px + pw)
        y1 = float(py + ph)

        vertices = np.array([
            x0, y0, 0.0, 1.0,
            x0, y1, 0.0, 0.0,
            x1, y0, 1.0, 1.0,
            x1, y0, 1.0, 1.0,
            x0, y1, 0.0, 0.0,
            x1, y1, 1.0, 0.0,
        ], dtype='f4')
        self.vbo.write(vertices.tobytes())
        self._portrait_texture.use(0)
        self.vao.render(moderngl.TRIANGLES)

    @staticmethod
    def _clamp01(v: float) -> float:
        return max(0.0, min(1.0, v))

    def _load_balloon_assets(self):
        """Load balloon sprite sheet and config."""
        ui_dir = os.path.join("assets", "images", "ui")
        config_path = os.path.join(ui_dir, "dialog_balloon.json")
        sheet_path = os.path.join(ui_dir, "dialog_balloon.png")

        if not os.path.exists(config_path) or not os.path.exists(sheet_path):
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._balloon_config = json.load(f)
            sheet = load_image_surface(sheet_path)
            self._balloon_sprites = self._slice_balloon_sprites(sheet, self._balloon_config)
        except Exception:
            self._balloon_config = None
            self._balloon_sprites = {}

    def _slice_balloon_sprites(self, sheet: SoftwareSurface, config: Dict) -> Dict[str, SoftwareSurface]:
        sprites = {}
        for name, info in config.get("sprites", {}).items():
            rect = info.get("rect")
            if not rect or len(rect) != 4:
                continue
            x, y, w, h = rect
            sprite = SoftwareSurface(w, h)
            sprite.blit(sheet, (0, 0), (x, y, w, h))
            sprites[name] = sprite
        return sprites

    def _load_character_portraits(self):
        """Load character portrait images from assets/images/character/"""
        char_dir = os.path.join("assets", "images", "character")
        if not os.path.isdir(char_dir):
            return

        for char_name in os.listdir(char_dir):
            char_path = os.path.join(char_dir, char_name)
            if not os.path.isdir(char_path):
                continue

            config_path = os.path.join(char_path, "character.json")
            if not os.path.exists(config_path):
                continue

            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                self._portrait_configs[char_name] = config

                for portrait_key, portrait_info in config.get("portraits", {}).items():
                    file_path = portrait_info.get("file")
                    if not file_path:
                        continue
                    full_path = os.path.join(char_dir, file_path)
                    if os.path.exists(full_path):
                        img = load_image_surface(full_path)
                        self._character_portraits[f"{char_name}/{portrait_key}"] = img
            except Exception as e:
                print(f"[DialogGLRenderer] Failed to load character {char_name}: {e}")

    def _render_balloon_surface(
        self,
        sentence,
        visible_chars: int,
        frame_counter: int
    ) -> Tuple[SoftwareSurface, Tuple[int, int, int, int]]:
        """
        Render balloon dialog surface and target quad rect.

        纹理结构（按图集 x 坐标排列）：
        - "body" sprite (x=0): 左侧是 body 可平铺区，右侧(center_x 之后)是尾巴帽
        - "head" sprite (x=108): 左侧(0 到 center_x)是头部帽，右侧是 body 可平铺区
        - 组装: [HEAD_CAP] + [BODY_TILE × N] + [TAIL_CAP]
        """
        style = max(1, int(getattr(sentence, "balloon_style", 1) or 1))
        style_key = f"style_{style}"
        style_cfg = (self._balloon_config or {}).get("balloon_styles", {}).get(style_key)
        if not style_cfg:
            return None, self._quad_rect

        sprites_cfg = (self._balloon_config or {}).get("sprites", {})
        layout = (self._balloon_config or {}).get("layout_params", {})
        scale_frames = int(layout.get("scale_animation_frames", 10))
        text_color = tuple(layout.get("text_color", [0, 0, 0]))

        full_text = sentence.text or ""
        visible_text = full_text[:visible_chars]

        is_multi = style_cfg.get("type") == "multi_line"

        # --- 获取 sprite ---
        head_name = style_cfg["head"]
        tail_name = style_cfg["body"]

        head_sprite = self._balloon_sprites.get(head_name)
        tail_sprite = self._balloon_sprites.get(tail_name)
        if not head_sprite or not tail_sprite:
            return None, self._quad_rect

        head_info = sprites_cfg.get(head_name, {})
        tail_info = sprites_cfg.get(tail_name, {})

        head_center_x = head_info.get("center", [head_sprite.get_width() // 3])[0]
        tail_center_x = tail_info.get("center", [tail_sprite.get_width() // 2])[0]

        head_w = head_sprite.get_width()
        tail_w = tail_sprite.get_width()
        sprite_h = head_sprite.get_height()

        # --- 切分 cap 和 body tile ---
        head_cap_w = int(style_cfg.get("head_cap_width", head_center_x))
        tail_cap_w = int(style_cfg.get("tail_cap_width", tail_w - tail_center_x))

        tile_width = int(style_cfg.get("body_repeat_width", 16))
        tile_x = int(style_cfg.get("body_tile_offset", head_center_x))
        if tile_x + tile_width > head_w:
            tile_x = max(0, head_w - tile_width)
        actual_tile_w = min(tile_width, head_w - tile_x)
        if actual_tile_w <= 0:
            actual_tile_w = 1

        body_tile = SoftwareSurface(actual_tile_w, sprite_h)
        body_tile.blit(head_sprite, (0, 0), (tile_x, 0, actual_tile_w, sprite_h))

        # --- 计算文本行和字符数 ---
        full_lines = self._split_lines(full_text, 2 if is_multi else 1)
        line_lengths = [len(line) for line in full_lines]
        visible_lines = self._apply_visible_text(visible_text, line_lengths)
        max_chars = max(line_lengths) if line_lengths else 0
        if max_chars <= 0:
            max_chars = 1

        # --- 组装气泡 ---
        body_total_w = actual_tile_w * max_chars
        bubble_width = head_cap_w + body_total_w + tail_cap_w
        bubble_height = sprite_h

        bubble_surface = SoftwareSurface(bubble_width, bubble_height)

        # 1) HEAD CAP（head sprite 的左侧 head_cap_w 像素）
        bubble_surface.blit(head_sprite, (0, 0),
                            (0, 0, head_cap_w, sprite_h))

        # 2) BODY TILES（平铺）
        x = head_cap_w
        for _ in range(max_chars):
            bubble_surface.blit(body_tile, (x, 0))
            x += actual_tile_w

        # 3) TAIL CAP（tail sprite 的右侧 tail_cap_w 像素）
        tail_start = tail_w - tail_cap_w
        bubble_surface.blit(tail_sprite, (x, 0),
                            (tail_start, 0, tail_cap_w, sprite_h))

        # --- 渲染文字 ---
        line_height = self.balloon_font.get_linesize()
        text_block_height = line_height * len(full_lines)
        text_y = max(0, (bubble_height - text_block_height) // 2)
        text_x = head_cap_w + 4

        for line in visible_lines:
            if line:
                text_surface = self.balloon_font.render(line, True, text_color)
                bubble_surface.blit(text_surface, (text_x, text_y))
            text_y += line_height

        # 缩放动画
        if scale_frames > 0:
            scale = min(1.0, frame_counter / float(scale_frames))
        else:
            scale = 1.0
        if scale < 1.0:
            scaled_w = max(1, int(bubble_width * scale))
            scaled_h = max(1, int(bubble_height * scale))
            bubble_surface = SoftwareSurface.smoothscale(bubble_surface, (scaled_w, scaled_h))
            bubble_width, bubble_height = bubble_surface.get_size()

        # 窗口坐标定位
        gx, gy, gw, gh = self.game_viewport
        pos_x, pos_y = self._get_balloon_position(sentence)
        center_x = gx + pos_x
        center_y = gy + pos_y
        quad_x = int(center_x - bubble_width / 2)
        quad_y = int(center_y - bubble_height / 2)

        return bubble_surface, (quad_x, quad_y, bubble_width, bubble_height)

    def _split_lines(self, text: str, max_lines: int) -> list:
        """Split text into fixed number of lines without resizing bubble during typing."""
        if max_lines <= 1:
            return [text]
        if not text:
            return ["", ""]
        midpoint = (len(text) + 1) // 2
        return [text[:midpoint], text[midpoint:]]

    def _apply_visible_text(self, visible_text: str, line_lengths: list) -> list:
        """Map visible text onto precomputed line lengths."""
        lines = []
        remaining = visible_text
        for length in line_lengths:
            if length <= 0:
                lines.append("")
                continue
            lines.append(remaining[:length])
            remaining = remaining[length:]
        return lines

    def _get_balloon_position(self, sentence) -> Tuple[int, int]:
        """Get balloon position in game viewport coordinates."""
        if getattr(sentence, "balloon_x", None) is not None and getattr(sentence, "balloon_y", None) is not None:
            return int(sentence.balloon_x), int(sentence.balloon_y)
        if getattr(sentence, "position", "left") == "right":
            return self._balloon_default_right
        return self._balloon_default_left

    def cleanup(self):
        """释放 GL 资源"""
        if self._dialog_texture:
            self._dialog_texture.release()
            self._dialog_texture = None
        if self._portrait_texture:
            self._portrait_texture.release()
            self._portrait_texture = None
