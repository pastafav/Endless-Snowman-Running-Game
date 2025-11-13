# person3_ui/screens.py
import os
import pygame as pg

BG_PATH = os.path.join("assets", "snow_background.jpg")  # เปลี่ยน path ได้

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
        self.button_start = pg.Rect(0, 0, 180, 56)
        self.button_howto = pg.Rect(0, 0, 220, 46)

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
        if ev.type == pg.KEYDOWN and ev.key in (pg.K_RETURN, pg.K_KP_ENTER):
            return {"action": "start_game"}
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

        # ปุ่ม START
        self.button_start.center = (w // 2, h // 2 + 20)
        pg.draw.rect(surf, (120, 160, 255), self.button_start, border_radius=18)
        pg.draw.rect(surf, (60, 100, 200),  self.button_start, width=3, border_radius=18)
        btn_text = self.font.render("START", True, (255, 255, 255))
        surf.blit(btn_text, btn_text.get_rect(center=self.button_start.center))

        # ปุ่ม HOW TO PLAY (อยู่ใต้ START)
        self.button_howto.center = (w // 2, h // 2 + 90)
        pg.draw.rect(surf, (255, 255, 255, 220), self.button_howto, border_radius=14)
        pg.draw.rect(surf, (60, 100, 200),      self.button_howto, width=2, border_radius=14)
        howto_text = self.font.render("HOW TO PLAY", True, (60, 100, 200))
        surf.blit(howto_text, howto_text.get_rect(center=self.button_howto.center))


# ---------- How To Play ----------
class HowToScene:
    def __init__(self, font):
        self.font = font
        self.small_font = pg.font.SysFont(None, 20)

        if os.path.exists(BG_PATH):
            self.bg_original = pg.image.load(BG_PATH).convert()
        else:
            self.bg_original = None
        self.bg = None
        self.bg_size = None

        # ปุ่ม BACK
        self.button_back = pg.Rect(0, 0, 160, 46)

        self.lines = [
            "Use LEFT / RIGHT or A / D to move.",
            "Press P to pause the game.",
            "Avoid trees and obstacles.",
            "Collect presents and special items.",
            "Enter igloos to go to special maps.",
            "In Hell mode, survive before the snowman melted",
        ]

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
        if ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
            if self.button_back.collidepoint(ev.pos):
                return {"action": "back_to_title"}
        return None

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

        # แสดงข้อความทีละบรรทัด
        y = tpos.bottom + 20
        for line in self.lines:
            txt = self.small_font.render(line, True, (20, 40, 70))
            surf.blit(txt, (panel_rect.x + 40, y))
            y += 30

        # ปุ่ม BACK
        self.button_back.center = (panel_rect.centerx, panel_rect.bottom - 40)
        pg.draw.rect(surf, (120, 160, 255), self.button_back, border_radius=14)
        pg.draw.rect(surf, (60, 100, 200),  self.button_back, width=2, border_radius=14)
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
