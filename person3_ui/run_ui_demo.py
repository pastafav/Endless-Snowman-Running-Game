# person3_ui/run_ui_demo.py
# Controls:
# ENTER/Click start = begin,  P = pause/resume,  H = toggle Hell/Normal,
# C = +coin, I/J = +3/+10 survival,  K = hit (lose heart),
# R = reset (on GameOver),  ESC/Close = quit

import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pygame as pg
from main_game import config as C
from person3_ui.hud import HUD
from person3_ui.screens import GameOverScene, PauseScene, TitleScene


def center_at(surf, text_surface, y=None):
    rect = text_surface.get_rect()
    x = (C.WIDTH - rect.width) // 2
    if y is None:
        y = (C.HEIGHT - rect.height) // 2
    return (x, y)


def main():
    pg.init()
    pg.font.init()
    screen = pg.display.set_mode((C.WIDTH, C.HEIGHT))
    pg.display.set_caption("OLAF – UI Demo (Auto Mode Switch + Hell hold)")
    clock = pg.time.Clock()

    # ฟอนต์ 2 ขนาด
    font_title = pg.font.Font(C.FONT_NAME, 32)  # Title / Pause / Game Over
    font_hud   = pg.font.Font(C.FONT_NAME, 22)  # HUD + hint ระหว่างเล่น

    # Scenes & HUD
    hud = HUD(font_hud)
    title_scene = TitleScene(font_title)
    pause_scene = PauseScene(font_title)
    gameover_scene = GameOverScene(font_title)

    # ===== Auto toggle settings =====
    AUTO_TOGGLE_INTERVAL = getattr(C, "AUTO_TOGGLE_INTERVAL", 7.0)  # เวลารอใน Normal -> เข้าสู่ Hell
    HELL_DURATION        = getattr(C, "HELL_DURATION",        5.0)  # เวลาค้างใน Hell -> กลับ Normal

    normal_timer = 0.0  # นับเฉพาะตอนอยู่ Normal
    hell_timer   = 0.0  # นับเฉพาะตอนอยู่ Hell

    scene = "title"
    running = True
    print("[INFO] Demo started.")

    while running:
        dt = clock.tick(C.FPS) / 1000.0

        # ===== UPDATE =====
        if scene == "playing":
            hud.update(dt)              # survival bar decay (หยุดเมื่อ pause)
            hud.add_distance(5.5 * dt)  # จำลองการวิ่งไปข้างหน้า

            # ---- Auto mode logic ----
            if hud.mode == "normal":
                # เดินเวลาเฉพาะ normal
                normal_timer += dt
                hell_timer = 0.0  # กันไว้ไม่ให้มีค่าค้าง
                if normal_timer >= AUTO_TOGGLE_INTERVAL:
                    hud.set_mode("hell")
                    print(f"[AUTO] Enter Hell")
                    normal_timer = 0.0  # รีเซ็ต พร้อมไปนับใหม่เมื่อกลับ normal
                    hell_timer = 0.0    # เริ่มจับเวลาใน hell
            else:  # hud.mode == "hell"
                hell_timer += dt
                normal_timer = 0.0
                if hell_timer >= HELL_DURATION:
                    hud.set_mode("normal")
                    print(f"[AUTO] Exit Hell → Normal")
                    hell_timer = 0.0
                    normal_timer = 0.0  # เริ่มนับรอรอบใหม่ใน normal

            # ตายเพราะ survival bar หมด
            if hud.hell_survival <= 0:
                print(f"[INFO] GO by survival: score={hud.score} dist={hud.distance:.1f}")
                scene = "gameover"
                gameover_scene.on_enter(score=int(hud.score), distance=int(hud.distance))

        # ===== EVENTS =====
        for ev in pg.event.get():
            if ev.type == pg.QUIT:
                running = False

            elif ev.type == pg.KEYDOWN and ev.key == pg.K_ESCAPE:
                running = False

            # Title -> delegate ให้ TitleScene
            if scene == "title":
                action = title_scene.handle_event(ev)
                if action and action.get("action") == "start_game":
                    # เริ่มเล่นเสมอที่ Normal
                    hud.set_mode("normal")
                    normal_timer = 0.0
                    hell_timer = 0.0
                    scene = "playing"
                    print("[INFO] Start → playing")

            elif scene == "playing":
                if ev.type == pg.KEYDOWN:
                    if ev.key == pg.K_p:
                        scene = "pause"
                        print("[INFO] Pause")
                    elif ev.key == pg.K_h:
                        # Manual toggle + รีเซ็ตตัวจับเวลาที่เกี่ยวข้อง
                        if hud.mode == "normal":
                            hud.set_mode("hell")
                            hell_timer = 0.0
                            normal_timer = 0.0
                            print("[INFO] Toggle → Hell")
                        else:
                            hud.set_mode("normal")
                            normal_timer = 0.0
                            hell_timer = 0.0
                            print("[INFO] Toggle → Normal")
                        # หมายเหตุ: เมื่อกลับ Normal แล้ว ตัวจับเวลาจะเริ่มนับหา Hell รอบใหม่ตาม AUTO_TOGGLE_INTERVAL
                    elif ev.key == pg.K_c:
                        hud.add_coin(1)
                    elif ev.key == pg.K_i:
                        hud.delta_hell_survival(+3.0)
                    elif ev.key == pg.K_j:
                        hud.delta_hell_survival(+10.0)
                    elif ev.key == pg.K_k:
                        hud.lose_life(1)
                        print(f"[INFO] Hit → hearts={hud.hearts}")
                        if hud.hearts <= 0:
                            print(f"[INFO] GO by hearts: score={hud.score} dist={hud.distance:.1f}")
                            scene = "gameover"
                            gameover_scene.on_enter(score=int(hud.score), distance=int(hud.distance))

            elif scene == "pause":
                if ev.type == pg.KEYDOWN and ev.key == pg.K_p:
                    scene = "playing"
                    print("[INFO] Resume")
                    # ไม่ต้องแตะ timers เพราะเราไม่อัปเดตตอน pause อยู่แล้ว (มันหยุดเอง)

            elif scene == "gameover":
                if ev.type == pg.KEYDOWN and ev.key == pg.K_r:
                    # รีเซ็ต HUD ด้วยฟอนต์ HUD
                    hud = HUD(font_hud)
                    # รีเซ็ตตัวจับเวลา auto toggle
                    normal_timer = 0.0
                    hell_timer = 0.0
                    scene = "title"
                    print("[INFO] Reset → title")

        # ===== DRAW =====
        if scene == "title":
            title_scene.draw(screen)

        elif scene == "playing":
            screen.fill((25, 35, 60))
            hud.draw(screen)
            hint = font_hud.render(
                "[P]ause  [H]ell  [C]oin  [I/J] Ice  [K] Hit  [R]eset", True, C.WHITE
            )
            screen.blit(hint, (16, C.HEIGHT - 40))

        elif scene == "pause":
            screen.fill((25, 35, 60))
            hud.draw(screen)        # HUD ค้างเฉย ๆ (เราไม่เรียก hud.update ตอน pause)
            pause_scene.draw(screen)

        elif scene == "gameover":
            gameover_scene.draw(screen)

        pg.display.flip()

    pg.quit()


if __name__ == "__main__":
    main()
