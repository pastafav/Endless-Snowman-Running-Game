# person3_ui/hud.py
import os
import pygame as pg
from main_game import config as C

# ---------- helpers ----------
def _load_img(path, size=None, colorkey=None):
    """โหลดรูป ถ้าไม่มีไฟล์จะคืน None; ถ้ามี size จะสเกลให้"""
    try:
        if not os.path.exists(path):
            return None
        img = pg.image.load(path).convert_alpha()
        if size is not None:
            img = pg.transform.smoothscale(img, (size, size))
        if colorkey is not None:
            img.set_colorkey(colorkey)
        return img
    except Exception:
        return None


def _round_rect(surf, rect, color, radius=8, width=0):
    """วาดสี่เหลี่ยมมุมโค้ง (ใช้สำหรับบาร์)"""
    pg.draw.rect(surf, color, rect, width=width, border_radius=radius)


# ---------- HUD ----------
class HUD:
    def __init__(self, font: pg.font.Font):
        self.font = font

        # สถานะพื้นฐาน
        self.hearts = C.START_HEARTS
        self.mode = "normal"  # "normal" | "hell"
        self.hell_survival = C.HELL_SURVIVAL_MAX
        self.distance = 0.0   # ใช้ใน draw() และ add_distance()

        # โหลด asset
        self.heart_full = _load_img(C.HEART_FULL_PATH, C.ICON_SIZE)
        self.heart_empty = _load_img(C.HEART_EMPTY_PATH, C.ICON_SIZE)

        # layout
        self.x0 = C.UI_MARGIN
        self.y0 = C.UI_MARGIN
        self.line_gap = 28

    # ---------- update logic ----------
    def set_mode(self, mode: str):
        """เปลี่ยนโหมด ไม่รีเซ็ตค่า bar"""
        self.mode = mode

    def update(self, dt: float):
        """ให้ภายนอกจัดการ hell_survival เอง (เช่น map ใช้ melt sync เข้ามา)"""
        pass

    # ---------- basic stats ----------
    def lose_life(self, n: int = 1):
        self.hearts = max(0, self.hearts - int(n))

    def add_distance(self, d: float):
        self.distance += max(0.0, float(d))

    def set_hell_survival(self, t: float):
        self.hell_survival = max(0.0, min(C.HELL_SURVIVAL_MAX, float(t)))

    def delta_hell_survival(self, dt: float):
        self.set_hell_survival(self.hell_survival + float(dt))

    # ---------- draw ----------
    def draw(self, surf: pg.Surface):
        x = self.x0
        y = self.y0

        # Hearts 
        if self.mode == "hell":
            hearts_y = 120   # โหมด hell ให้ลงมาหน่อย ไม่ชน Melt text
        else:
            hearts_y = 100   # โหมดปกติ

        self._draw_hearts(surf, x, hearts_y)

        # Survival Bar (อยู่กลางด้านบนของหน้าจอ)
        self._draw_survival_bar(surf)

    # ---------- sub-components ----------
    def _draw_hearts(self, surf: pg.Surface, x: int, y: int):
        gap = 10
        for i in range(C.START_HEARTS):
            px = x + i * (C.ICON_SIZE + gap)
            is_full = (i < self.hearts)
            img = self.heart_full if is_full else self.heart_empty
            if img:
                surf.blit(img, (px, y))
            else:
                color = C.RED if is_full else (160, 160, 160)
                pg.draw.polygon(
                    surf, color,
                    [(px + 6, y + 10), (px + 12, y + 4),
                     (px + 18, y + 10), (px + 12, y + 22)]
                )
                pg.draw.circle(surf, color, (px + 10, y + 10), 6)
                pg.draw.circle(surf, color, (px + 14, y + 10), 6)

    def _draw_survival_bar(self, surf: pg.Surface):
        """แถบ survival: ฟ้าใน normal, ส้มใน hell, อยู่บนกลางจอ"""
        bar_w, bar_h = 360, 18

        # ใช้ขนาดจริงของ surface แทน C.WIDTH / C.HEIGHT
        surf_w, surf_h = surf.get_size()

        # คำนวณตำแหน่งให้อยู่ตรงกลางด้านบน
        x = (surf_w - bar_w) // 2
        y = 20  # ระยะจากขอบบน

        bg_rect = pg.Rect(x, y, bar_w, bar_h)

        # พื้นหลังเทา
        _round_rect(surf, bg_rect, C.UI_BG_GREY, radius=9, width=0)

        # สีตามโหมด
        if self.mode == "hell":
            fill_color = (245, 166, 66)  # ส้มอ่อน
            outline_color = (180, 100, 30)
        else:
            fill_color = C.UI_FILL_BLUE  # ฟ้า
            outline_color = C.UI_OUTLINE

        # คำนวณสัดส่วน
        ratio = 0 if C.HELL_SURVIVAL_MAX <= 0 else self.hell_survival / C.HELL_SURVIVAL_MAX
        ratio = max(0.0, min(1.0, ratio))
        fill_rect = pg.Rect(x, y, int(bar_w * ratio), bar_h)

        # วาดบาร์
        _round_rect(surf, fill_rect, fill_color, radius=9, width=0)
        _round_rect(surf, bg_rect, outline_color, radius=9, width=2)

        # label อยู่เหนือบาร์ (ใช้ surf_w)
        label = self.font.render("Survival", True, C.WHITE)
        label_x = (surf_w - label.get_width()) // 2
        surf.blit(label, (label_x, y - 24))
