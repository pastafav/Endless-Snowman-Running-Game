import os

# ===== Screen & FPS =====
WIDTH = 800
HEIGHT = 480
FPS = 60
FONT_NAME = os.path.join("assets", "fonts", "PixelifySans-Regular.ttf")


# ===== Colors =====
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY  = (40, 40, 40)
RED   = (220, 60, 60)
GREEN = (60, 200, 120)
BLUE  = (70, 140, 240)
CYAN  = (80, 220, 220)
ORANGE = (240, 160, 60)
UI_BG_GREY = (90, 96, 110)      # สำหรับพื้นบาร์
UI_FILL_BLUE = (120, 190, 255)  # ฟ้าในบาร์
UI_OUTLINE = (25, 81, 171)      # น้ำเงินกรอบบาร์

# ===== HUD Defaults =====
START_HEARTS = 3
HELL_SURVIVAL_MAX = 20.0
SCORE_PER_COIN = 10


# ===== UI Layout & Assets =====
UI_MARGIN = 16
ICON_SIZE = 24  # ขนาดหัวใจ/เหรียญหลังสเกล
ASSETS_ROOT = "assets"
HEART_FULL_PATH = f"{ASSETS_ROOT}/ui/heart_full.png"
HEART_EMPTY_PATH = f"{ASSETS_ROOT}/ui/heart_empty.png"
COIN_ICON_PATH = f"{ASSETS_ROOT}/items/coin.png"

HELL_SURVIVAL_MAX = 20.0
# อัตราลดต่อวินาที
SURVIVAL_DECAY_HELL    = 1.0   # ลดเร็วตอน Hell
SURVIVAL_DECAY_NORMAL  = 1.0  # ลดช้าตอน Normal (ปรับได้)

AUTO_TOGGLE_INTERVAL = 7.0  # วินาทีที่อยู่ Normal ก่อนเข้าถึง Hell อัตโนมัติ
HELL_DURATION        = 5.0  # วินาทีที่ค้างอยู่ใน Hell ก่อนกลับ Normal


