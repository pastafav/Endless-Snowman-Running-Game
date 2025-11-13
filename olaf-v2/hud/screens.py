import os
import pygame as pg

BG_PATH = os.path.join("image", "snow_background.jpg")  # เปลี่ยน path ได้

def center_at(surf, text_surface, y=None):
    """จัดกลางบน surface ตามขนาดจริงของหน้าต่าง"""
    w, h = surf.get_size()
    rect = text_surface.get_rect()
    x = (w - rect.width) // 2
    if y is None:
        y = (h - rect.height) // 2
    return (x, y)

def _round_rect(surf, rect, color, radius=12, width=0):
    """สี่เหลี่ยมมุมโค้ง ใช้สำหรับวาด panel/เงา"""
    pg.draw.rect(surf, color, rect, width=width, border_radius=radius)


# ---------- Title ----------
class TitleScene:
    def __init__(self, font):
        self.font = font
        # โหลด BG แบบไม่ scale ก่อน
        if os.path.exists(BG_PATH):
            self.bg_original = pg.image.load(BG_PATH).convert()
        else:
            self.bg_original = None
        self.bg = None     # จะ scale ตอน draw ตามขนาดหน้าต่าง
        self.bg_size = None

        # ปุ่มต่าง ๆ (กำหนดตำแหน่งตอน draw)
        self.button_start = pg.Rect(0, 0, 200, 60)
        # Make HOW TO PLAY have more padding around text
        self.button_howto = pg.Rect(0, 0, 360, 64)

    def _ensure_bg_scaled(self, surf):
        """ถ้า BG ยังไม่ scale ให้ตรงกับขนาดหน้าต่าง ก็ scale ใหม่"""
        if not self.bg_original:
            self.bg = None
            return
        w, h = surf.get_size()
        if self.bg is None or self.bg_size != (w, h):
            self.bg = pg.transform.scale(self.bg_original, (w, h))
            self.bg_size = (w, h)

    def handle_event(self, ev):
        if ev.type == pg.KEYDOWN:
            if ev.key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE):
                return {"action": "start_game"}
            if ev.key in (pg.K_h, pg.K_F1):
                return {"action": "show_howto"}
        if ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
            if self.button_start.collidepoint(ev.pos):
                return {"action": "start_game"}
            if self.button_howto.collidepoint(ev.pos):
                return {"action": "show_howto"}
        return None

    def draw(self, surf):
        w, h = surf.get_size()

        # BG
        self._ensure_bg_scaled(surf)
        if self.bg:
            surf.blit(self.bg, (0, 0))
        else:
            surf.fill((135, 206, 235))

        # Title (ส้ม + เงา)
        title_text   = self.font.render("SNOW SURVIVOR", True, (255, 140, 0))
        title_shadow = self.font.render("SNOW SURVIVOR", True, (50, 50, 50))
        pos = title_text.get_rect(center=(w // 2, h // 2 - 60))
        surf.blit(title_shadow, (pos.x + 3, pos.y + 3))
        surf.blit(title_text, pos)

        # เอาตำแหน่งเมาส์มาใช้เช็ค hover
        mx, my = pg.mouse.get_pos()

        # ปุ่ม START
        self.button_start.center = (w // 2, h // 2 + 20)
        hovered_start = self.button_start.collidepoint(mx, my)

        if hovered_start:
            start_fill   = (140, 180, 255)  # สว่างขึ้น
            start_border = (40, 80, 180)
        else:
            start_fill   = (120, 160, 255)
            start_border = (60, 100, 200)

        pg.draw.rect(surf, start_fill, self.button_start, border_radius=18)
        pg.draw.rect(surf, start_border, self.button_start, width=3, border_radius=18)
        btn_text = self.font.render("START", True, (255, 255, 255))
        surf.blit(btn_text, btn_text.get_rect(center=self.button_start.center))

        # ปุ่ม HOW TO PLAY (อยู่ใต้ START)
        self.button_howto.center = (w // 2, h // 2 + 90)
        hovered_howto = self.button_howto.collidepoint(mx, my)

        if hovered_howto:
            howto_fill   = (235, 245, 255)   # ขาวอมฟ้า สว่าง
            howto_border = (40, 80, 180)
            howto_text_color = (40, 80, 180)
        else:
            howto_fill   = (255, 255, 255)   # ขาวปกติ
            howto_border = (60, 100, 200)
            howto_text_color = (60, 100, 200)

        pg.draw.rect(surf, howto_fill, self.button_howto, border_radius=14)
        pg.draw.rect(surf, howto_border, self.button_howto, width=2, border_radius=14)
        howto_text = self.font.render("HOW TO PLAY", True, howto_text_color)
        surf.blit(howto_text, howto_text.get_rect(center=self.button_howto.center))


# ---------- How To Play ----------
class HowToScene:
    def __init__(self, font):
        self.font = font
        self.small_font = pg.font.SysFont(None, 20)
        self.medium_font = pg.font.SysFont("consolas", 24)
        # scrolling state
        self.scroll_y = 0.0
        self._content_h = 0
        self._last_viewport_h = 0
        self._scroll_step = 60  # pixels per wheel notch / arrow key step

        if os.path.exists(BG_PATH):
            self.bg_original = pg.image.load(BG_PATH).convert()
        else:
            self.bg_original = None
        self.bg = None
        self.bg_size = None

        # ปุ่ม BACK
        self.button_back = pg.Rect(0, 0, 160, 46)

        # Assets for visual guidance
        self.tree_img = None
        self.present_img = None
        self.igloo_img = None
        self.snowman_img = None
        self.carrot_img = None
        self.moose_img = None
        self.icecube_img = None
        self.iceshard_img = None

        def _ld(name, w, h):
            try:
                img = pg.image.load(os.path.join("image", name)).convert_alpha()
                return pg.transform.scale(img, (w, h))
            except Exception as e:
                print(f"[HowTo] Cannot load {name}:", e)
                return None

        self.tree_img    = _ld("Tree_1.png", 32, 32)
        self.present_img = _ld("Present_1.png", 28, 28)
        self.igloo_img   = _ld("Igloo_2.png", 40, 40)
        self.snowman_img = _ld("Snowman_idle2.png", 44, 44)
        self.carrot_img  = _ld("Carrot_1.png", 36, 36)
        self.moose_img   = _ld("Moose_item_1.png", 36, 36)
        self.icecube_img = _ld("Icecube_1.png", 30, 30)
        self.iceshard_img= _ld("IceShards_1.png", 40, 40)

    def _ensure_bg_scaled(self, surf):
        if not self.bg_original:
            self.bg = None
            return
        w, h = surf.get_size()
        if self.bg is None or self.bg_size != (w, h):
            self.bg = pg.transform.scale(self.bg_original, (w, h))
            self.bg_size = (w, h)

    def handle_event(self, ev):
        if ev.type == pg.KEYDOWN and ev.key in (pg.K_ESCAPE, pg.K_BACKSPACE, pg.K_RETURN):
            return {"action": "back_to_title"}
        if ev.type == pg.KEYDOWN:
            # scroll with arrows / PageUp/PageDown / Home/End
            if ev.key == pg.K_DOWN:
                self.scroll_y += self._scroll_step
            elif ev.key == pg.K_UP:
                self.scroll_y -= self._scroll_step
            elif ev.key == pg.K_PAGEDOWN:
                self.scroll_y += self._scroll_step * 3
            elif ev.key == pg.K_PAGEUP:
                self.scroll_y -= self._scroll_step * 3
            elif ev.key == pg.K_END:
                self.scroll_y = float(max(0, self._content_h - self._last_viewport_h))
            elif ev.key == pg.K_HOME:
                self.scroll_y = 0.0
            self._clamp_scroll()
        if ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
            if self.button_back.collidepoint(ev.pos):
                return {"action": "back_to_title"}
        # Mouse wheel scroll
        if hasattr(pg, "MOUSEWHEEL") and ev.type == pg.MOUSEWHEEL:
            # In pygame, positive y is wheel up
            self.scroll_y -= ev.y * self._scroll_step
            self._clamp_scroll()
        return None

    def _clamp_scroll(self):
        if self._last_viewport_h <= 0:
            self.scroll_y = 0.0
            return
        max_scroll = max(0, self._content_h - self._last_viewport_h)
        self.scroll_y = max(0.0, min(float(max_scroll), float(self.scroll_y)))

    def _wrap_lines(self, text: str, font, max_w: int):
        words = text.split()
        lines = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if font.size(test)[0] <= max_w or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def draw(self, surf):
        w, h = surf.get_size()

        # BG เบลอ/จางเล็กน้อย
        self._ensure_bg_scaled(surf)
        if self.bg:
            surf.blit(self.bg, (0, 0))
        else:
            surf.fill((135, 206, 235))

        # overlay มืดบาง ๆ
        overlay = pg.Surface((w, h), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surf.blit(overlay, (0, 0))

        # กล่อง panel ตรงกลาง
        panel_w, panel_h = int(w * 0.7), int(h * 0.6)
        panel_rect = pg.Rect(0, 0, panel_w, panel_h)
        panel_rect.center = (w // 2, h // 2)

        shadow_surf = pg.Surface((panel_w, panel_h), pg.SRCALPHA)
        _round_rect(shadow_surf, shadow_surf.get_rect(), (0, 0, 0, 80), radius=16)
        surf.blit(shadow_surf, (panel_rect.x + 4, panel_rect.y + 6))

        _round_rect(surf, panel_rect, (210, 230, 255), radius=16, width=0)
        _round_rect(surf, panel_rect, (60, 100, 200), radius=16, width=2)

        # Title HOW TO PLAY
        title = self.font.render("HOW TO PLAY", True, (60, 100, 200))
        tpos = title.get_rect(center=(panel_rect.centerx, panel_rect.y + 40))
        surf.blit(title, tpos)

        # Prepare a scrollable content surface inside the panel
        padding = 24
        view_x = panel_rect.x + padding
        view_y = tpos.bottom + 12
        view_w = panel_rect.w - padding*2
        # Reserve space above BACK button and a little bottom padding
        back_space = 70
        view_h = max(60, panel_rect.bottom - back_space - view_y)
        self._last_viewport_h = view_h

        content = pg.Surface((view_w, 2000), pg.SRCALPHA)  # tall; we'll track y and clip later
        cx, cy = 6, 0

        def draw_icon_line(icon, text):
            nonlocal cy
            ix = cx
            # text wrapping
            max_w = view_w - 100  # provisional, will refine after icon width
            lines = self._wrap_lines(text, self.small_font, max_w)
            font_h = self.small_font.get_height()
            line_slot = font_h + 8
            text_block_h = max(line_slot, len(lines) * line_slot)
            icon_w = icon.get_width() if icon else 0
            icon_h = icon.get_height() if icon else 0
            block_h = max(text_block_h, icon_h)

            # place icon vertically centered in block
            if icon:
                iy = cy + (block_h - icon_h) // 2
                content.blit(icon, (ix, iy))
                ix += icon_w + 10

            # recompute wrapping with final left edge
            max_w = view_w - (ix - cx)
            lines = self._wrap_lines(text, self.small_font, max_w)
            # top offset to center text block within block_h
            ty = cy + (block_h - len(lines) * line_slot) // 2
            for ln in lines:
                surf_line = self.small_font.render(ln, True, (20, 40, 70))
                # center text within its line slot
                content.blit(surf_line, (ix, ty + (line_slot - font_h)//2))
                ty += line_slot

            cy += block_h + 8

        def draw_icons_line(icons, text):
            nonlocal cy
            icons = [ic for ic in (icons or []) if ic]
            ix = cx
            font_h = self.small_font.get_height()
            line_slot = font_h + 8

            # find max icon height and total icon width for left area
            max_icon_h = max((ic.get_height() for ic in icons), default=0)
            icons_w = sum(ic.get_width() for ic in icons) + (8 * max(0, len(icons)-1))

            # wrap text given remaining width
            max_w = view_w - (icons_w + 10)
            lines = self._wrap_lines(text, self.small_font, max_w)
            text_block_h = max(line_slot, len(lines) * line_slot)
            block_h = max(text_block_h, max_icon_h)

            # draw icons vertically centered in block
            for idx, ic in enumerate(icons):
                iy = cy + (block_h - ic.get_height()) // 2
                content.blit(ic, (ix, iy))
                ix += ic.get_width() + 8
            ix += 2  # extra breathing room before text

            # draw wrapped text centered in block
            ty = cy + (block_h - len(lines) * line_slot) // 2
            for ln in lines:
                surf_line = self.small_font.render(ln, True, (20, 40, 70))
                content.blit(surf_line, (ix, ty + (line_slot - font_h)//2))
                ty += line_slot

            cy += block_h + 8

        # Section: Movement
        head = self.medium_font.render("Movement", True, (40, 80, 160))
        content.blit(head, (cx, cy)); cy += 32
        box = pg.Rect(cx, cy, min(320, view_w-12), 44)
        _round_rect(content, box, (235, 242, 255), radius=8)
        _round_rect(content, box, (120, 160, 220), radius=8, width=2)
        tip = self.small_font.render("Use LEFT/RIGHT or A/D to switch lanes", True, (20, 40, 70))
        content.blit(tip, (box.x + 8, box.y + 12)); cy += 54
        draw_icons_line([self.tree_img, self.iceshard_img], "Dodge obstacles")
        draw_icon_line(self.present_img, "Collect presents to increase your score")

        # Section: Power-ups
        head = self.medium_font.render("Power-ups", True, (40, 80, 160))
        content.blit(head, (cx, cy)); cy += 32
        draw_icon_line(self.carrot_img, "Carrot: Split into parts; ignore obstacles; still collect presents.")
        draw_icon_line(self.moose_img,  "Moose: Speed boost; ignore obstacles; still collect presents.")

        # Section: Igloos & Hell
        head = self.medium_font.render("Igloos & Hell", True, (40, 80, 160))
        content.blit(head, (cx, cy)); cy += 32
        draw_icon_line(self.igloo_img, "Enter an igloo to play a mini-game, if you win, you will get bonus presents.")
        # reserve space equal to igloo icon so text aligns with the line above
        placeholder = pg.Surface(self.igloo_img.get_size(), pg.SRCALPHA) if self.igloo_img else pg.Surface((40, 40), pg.SRCALPHA)
        draw_icon_line(placeholder, "After done playing mini-game, you will enter the hell mode")
        draw_icon_line(self.icecube_img, "In hell mode, survive as the melt bar drains. Collect icecubes to extend time.")

        # Section: Controls
        head = self.medium_font.render("Controls", True, (40, 80, 160))
        content.blit(head, (cx, cy)); cy += 32
        for ln in self._wrap_lines("Pause/Resume: P    Back: ESC / Backspace", self.small_font, view_w-10):
            content.blit(self.small_font.render(ln, True, (20, 40, 70)), (cx, cy))
            cy += 28

        # Store content height and clamp scroll
        self._content_h = cy
        self._clamp_scroll()

        # Blit the scrollable area with clipping
        prev_clip = surf.get_clip()
        surf.set_clip(pg.Rect(view_x, view_y, view_w, view_h))
        surf.blit(content, (view_x, view_y - int(self.scroll_y)))
        surf.set_clip(prev_clip)

        # Draw a simple scrollbar on the right inside panel
        if self._content_h > view_h:
            bar_x = panel_rect.right - 10 - 6
            bar_y = view_y
            bar_w = 6
            bar_h = view_h
            pg.draw.rect(surf, (200, 210, 230), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
            ratio = view_h / max(1, self._content_h)
            thumb_h = max(24, int(bar_h * ratio))
            max_scroll = max(1, self._content_h - view_h)
            thumb_y = bar_y + int((bar_h - thumb_h) * (self.scroll_y / max_scroll))
            pg.draw.rect(surf, (120, 160, 220), (bar_x, thumb_y, bar_w, thumb_h), border_radius=3)

        # ปุ่ม BACK + hover
        self.button_back.center = (panel_rect.centerx, panel_rect.bottom - 30)

        mx, my = pg.mouse.get_pos()
        hovered = self.button_back.collidepoint(mx, my)

        if hovered:
            fill_color   = (140, 180, 255)  # สว่างขึ้น
            border_color = (40, 80, 180)
        else:
            fill_color   = (120, 160, 255)
            border_color = (60, 100, 200)

        pg.draw.rect(surf, fill_color, self.button_back, border_radius=14)
        pg.draw.rect(surf, border_color, self.button_back, width=2, border_radius=14)
        back_txt = self.font.render("BACK", True, (255, 255, 255))
        surf.blit(back_txt, back_txt.get_rect(center=self.button_back.center))


# ---------- Pause ----------
class PauseScene:
    def __init__(self, font):
        self.font = font

    def draw(self, surf):
        w, h = surf.get_size()
        overlay = pg.Surface((w, h), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surf.blit(overlay, (0, 0))
        t = self.font.render("PAUSED – Press P to resume", True, (255, 255, 255))
        surf.blit(t, center_at(surf, t))


# ---------- Game Over ----------
class GameOverScene:
    def __init__(self, font):
        self.font = font
        self.score = 0
        self.distance = 0

        if os.path.exists(BG_PATH):
            self.bg_original = pg.image.load(BG_PATH).convert()
        else:
            self.bg_original = None
        self.bg = None
        self.bg_size = None

        # Panel style
        self.panel_w, self.panel_h = 440, 160
        self.panel_radius = 16
        self.panel_color = (139, 168, 255)   # ฟ้าอ่อน
        self.panel_outline = (60, 100, 200)  # น้ำเงินเข้ม
        self.shadow_color = (0, 0, 0, 70)

    def _ensure_bg_scaled(self, surf):
        if not self.bg_original:
            self.bg = None
            return
        w, h = surf.get_size()
        if self.bg is None or self.bg_size != (w, h):
            self.bg = pg.transform.scale(self.bg_original, (w, h))
            self.bg_size = (w, h)

    def on_enter(self, score=0, distance=0):
        self.score = int(score)
        self.distance = int(distance)

    def draw(self, surf):
        w, h = surf.get_size()

        # BG
        self._ensure_bg_scaled(surf)
        if self.bg:
            surf.blit(self.bg, (0, 0))
        else:
            surf.fill((135, 206, 235))

        # Title "Game Over" (ส้ม + เงา)
        title  = self.font.render("GAME OVER", True, (255, 140, 0))
        shadow = self.font.render("GAME OVER", True, (50, 50, 50))
        pos = title.get_rect(center=(w // 2, h // 2 - 120))
        surf.blit(shadow, (pos.x + 3, pos.y + 3))
        surf.blit(title, pos)

        # Panel + shadow
        panel_rect = pg.Rect(0, 0, self.panel_w, self.panel_h)
        panel_rect.center = (w // 2, h // 2)

        shadow_surf = pg.Surface((self.panel_w, self.panel_h), pg.SRCALPHA)
        _round_rect(shadow_surf, shadow_surf.get_rect(), self.shadow_color, radius=self.panel_radius)
        surf.blit(shadow_surf, (panel_rect.x + 4, panel_rect.y + 6))

        _round_rect(surf, panel_rect, self.panel_color, radius=self.panel_radius, width=0)
        _round_rect(surf, panel_rect, self.panel_outline, radius=self.panel_radius, width=3)

        # Texts inside panel
        s_score = self.font.render(f"SCORE: {self.score}", True, (255, 255, 255))
        s_dist  = self.font.render(f"DISTANCE: {self.distance}", True, (255, 255, 255))
        surf.blit(s_score, (panel_rect.x + 28, panel_rect.y + 34))
        surf.blit(s_dist,  (panel_rect.x + 28, panel_rect.y + 88))

        # Hint
        hint = self.font.render("PRESS R TO RESTART", True, (35, 68, 150))
        surf.blit(hint, center_at(surf, hint, h // 2 + self.panel_h // 2 + 40))
