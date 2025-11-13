from __future__ import annotations
import time
import pygame
import os, sys

# --- ให้ Python มองเห็นโฟลเดอร์ parent (ที่มี hud / image อยู่) ---
ROOT = os.path.dirname(os.path.abspath(__file__))   # .../Endless-Snowman-Running-Game/olaf-v2
PARENT = os.path.dirname(ROOT)                      # .../Endless-Snowman-Running-Game
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)
# ---------------------------------------------------------------

# ── Window / timing ───────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1280, 720
FPS = 60
SWITCH_INTERVAL = 20.0   # seconds between automatic scene changes when playing
START_SCENE = "snowy"    # always begin & restart here

ICON_SIZE = 32  # ขนาด icon HUD (heart/present)

# ── Import scenes (package-relative) ──────────────────────────────────────────
from snowman.scenes.snowy import SnowyScene
from snowman.scenes.hell  import HellScene

# ── Import UI screens ของคุณ ─────────────────────────────────────────────────
from hud.screens import (
    TitleScene,
    HowToScene,
    PauseScene,
)


# ── Simple UI button ─────────────────────────────────────────────────────────
class Button:
    def __init__(self, rect: pygame.Rect, text: str, on_click):
        self.rect = rect
        self.text = text
        self.on_click = on_click
        self.font = pygame.font.SysFont("consolas", 28)

    def draw(self, surf: pygame.Surface, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        base = (30, 30, 30)
        fill = (240, 240, 240) if hovered else (210, 210, 210)
        outline = (60, 60, 60)
        pygame.draw.rect(surf, fill, self.rect, border_radius=12)
        pygame.draw.rect(surf, outline, self.rect, 2, border_radius=12)
        txt = self.font.render(self.text, True, base)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                self.on_click()


# ── Scene manager ────────────────────────────────────────────────────────────
class SceneManager:
    def __init__(self, screen: pygame.Surface, scene_classes: dict[str, type]):
        self.screen = screen
        self.scene_classes = scene_classes   # {"snowy": SnowyScene, "hell": HellScene}
        self.instances: dict[str, object] = {}
        self.current_name: str | None = None
        self.current = None

        # Shared, cross-scene state (persists unless we reset it)
        self.shared = {"hearts": 3, "presents": 0, "ice": 0}

        # Run-timer (reset on restart_to_start)
        self._run_start_time: float = time.perf_counter()

    # ── shared/run-time control ───────────────────────────────────────────────
    def _reset_shared(self):
        """Fresh run values when starting or user presses Restart."""
        self.shared.update({"hearts": 3, "presents": 0, "ice": 0})

    def restart_to_start(self):
        """Always restart from the very beginning in START_SCENE."""
        self._reset_shared()
        self._run_start_time = time.perf_counter()
        self.switch_to(START_SCENE, reset=True)

    def get_run_seconds(self) -> float:
        return max(0.0, time.perf_counter() - self._run_start_time)

    # ── scene switching ───────────────────────────────────────────────────────
    def switch_to(self, name: str, *, reset: bool = True):
        if name not in self.scene_classes:
            print(f"[SceneManager] Unknown scene: {name}")
            return

        # Deactivate old (optional)
        if self.current and hasattr(self.current, "on_deactivate"):
            try:
                self.current.on_deactivate()
            except Exception as e:
                print(f"[SceneManager] on_deactivate error in '{self.current_name}': {e}")

        # Get/create instance
        scene = self.instances.get(name)
        if scene is None:
            scene_cls = self.scene_classes[name]
            scene = scene_cls()
            # inject shared state
            if hasattr(scene, "set_shared"):
                scene.set_shared(self.shared)
            else:
                scene.shared = self.shared
            # start lifecycle
            if hasattr(scene, "start"):
                scene.start()
            self.instances[name] = scene
        elif reset and hasattr(scene, "reset"):
            # Reset ONLY scene-local stuff; shared is managed separately
            scene.reset()

        # Ensure scene is immediately live (not paused/start overlays)
        for attr in ("show_start", "paused", "game_over", "in_minigame"):
            if hasattr(scene, attr):
                setattr(scene, attr, False)

        self.current_name = name
        self.current = scene
        pygame.display.set_caption(f"Snow Survivor — {name.upper()}")

        if hasattr(scene, "on_activate"):
            try:
                scene.on_activate()
            except Exception as e:
                print(f"[SceneManager] on_activate error in '{name}': {e}")

        print(f"[SceneManager] Switched to '{name}'")

    # ── plumbing ──────────────────────────────────────────────────────────────
    def is_game_over(self) -> bool:
        return bool(getattr(self.current, "game_over", False))

    def handle_event(self, event: pygame.event.Event):
        if self.current and hasattr(self.current, "handle_event"):
            self.current.handle_event(event)

    def update(self, dt: float):
        if self.current and hasattr(self.current, "update"):
            self.current.update(dt)

    def draw(self):
        if self.current and hasattr(self.current, "draw"):
            self.current.draw(self.screen)
        else:
            self.screen.fill((25, 25, 25))


# ── HUD helpers ──────────────────────────────────────────────────────────────
def draw_overlay(screen: pygame.Surface, text: str, y: int):
    font = pygame.font.SysFont("consolas", 18)
    surf = font.render(text, True, (235, 235, 235))
    screen.blit(surf, (10, y))

def fmt_mmss(seconds: float) -> str:
    s = int(round(seconds))
    m, s = divmod(s, 60)
    return f"{m:02d}:{s:02d}"


# ── main loop ────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    pygame.display.set_caption("Snow Survivor — Scene Switcher")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    scenes = {"snowy": SnowyScene, "hell": HellScene}
    manager = SceneManager(screen, scenes)

    # ฟอนต์สำหรับ UI screens และ HUD
    ui_font = pygame.font.SysFont("consolas", 40, bold=True)
    small_font = pygame.font.SysFont("consolas", 20)

    # UI Scenes ของคุณ
    title_scene = TitleScene(ui_font)
    howto_scene = HowToScene(ui_font)
    pause_scene = PauseScene(ui_font)

    # โหลด icon HUD
    heart_full = pygame.image.load(
        os.path.join(ROOT, "image", "heart_full.png")
    ).convert_alpha()
    heart_empty = pygame.image.load(
        os.path.join(ROOT, "image", "heart_empty.png")
    ).convert_alpha()
    present_img = pygame.image.load(
        os.path.join(ROOT, "image", "Present_2.png")
    ).convert_alpha()

    # ย่อขนาดให้พอดี HUD
    heart_full = pygame.transform.scale(heart_full, (ICON_SIZE, ICON_SIZE))
    heart_empty = pygame.transform.scale(heart_empty, (ICON_SIZE, ICON_SIZE))
    present_img = pygame.transform.scale(present_img, (ICON_SIZE, ICON_SIZE))

    # เริ่มเกม: อยู่ Title ก่อน ยังไม่ start scene
    running = True
    show_game_over_menu = False
    show_title_screen   = True
    show_howto_screen   = False
    show_pause_menu     = False

    last_time = time.perf_counter()
    elapsed_since_switch = 0.0

    # ปุ่มใน Game Over menu (ใช้ overlay แบบเดิม)
    btn_w, btn_h = 240, 64
    spacing = 30
    cx, cy = WIDTH // 2, HEIGHT // 2 + 90

    def do_restart():
        nonlocal show_game_over_menu, elapsed_since_switch, show_pause_menu, show_title_screen, show_howto_screen
        manager.restart_to_start()
        show_game_over_menu = False
        show_pause_menu = False
        show_title_screen = False
        show_howto_screen = False
        elapsed_since_switch = 0.0

    def do_quit():
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    restart_btn = Button(pygame.Rect(cx - btn_w - spacing//2, cy, btn_w, btn_h),
                         "Restart (R)", do_restart)
    quit_btn    = Button(pygame.Rect(cx + spacing//2, cy, btn_w, btn_h),
                         "Quit (Q)",    do_quit)

    # ค่าที่ capture ตอน game over
    summary_time_sec = 0.0
    summary_presents = 0

    # Transition (fade) state
    transitioning = False
    transition_alpha = 0  # 0..255
    transition_target = None
    transition_speed = 800.0  # alpha units per second
    transition_phase = None   # 'out' or 'in'

    while running:
        now = time.perf_counter()
        dt = now - last_time
        last_time = now

        # auto-switch timer เดินเฉพาะตอนเล่นจริง
        if not (show_game_over_menu or show_title_screen or show_howto_screen or show_pause_menu):
            elapsed_since_switch += dt

        # ตรวจจับว่า scene ปัจจุบันเข้าสู่ game over
        if (
            not show_game_over_menu
            and not show_title_screen
            and not show_howto_screen
            and not show_pause_menu
            and manager.is_game_over()
        ):
            show_game_over_menu = True
            pygame.event.clear([pygame.KEYDOWN, pygame.KEYUP])
            summary_time_sec = manager.get_run_seconds()
            summary_presents = manager.shared.get("presents", 0)
            print("[UI] Game Over menu opened")

        # ── event handling ───────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            # ── TITLE SCREEN ───────────────────────────────────────────────
            if show_title_screen:
                result = title_scene.handle_event(event)
                if isinstance(result, dict):
                    action = result.get("action")
                    if action == "start_game":
                        manager.restart_to_start()
                        show_title_screen = False
                        show_howto_screen = False
                        elapsed_since_switch = 0.0
                    elif action == "show_howto":
                        show_howto_screen = True
                        show_title_screen = False
                continue  # ไม่ส่ง event ไปที่ scene

            # ── HOW TO PLAY SCREEN ────────────────────────────────────────
            if show_howto_screen:
                result = howto_scene.handle_event(event)
                if isinstance(result, dict) and result.get("action") == "back_to_title":
                    show_howto_screen = False
                    show_title_screen = True
                continue

            # ── GAME OVER MENU ────────────────────────────────────────────
            if show_game_over_menu:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_r, pygame.K_RETURN):
                        do_restart()
                    elif event.key in (pygame.K_q, pygame.K_ESCAPE):
                        running = False
                elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                    restart_btn.handle_event(event)
                    quit_btn.handle_event(event)
                continue

            # ── PAUSE MENU ────────────────────────────────────────────────
            if show_pause_menu:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        show_pause_menu = False
                    elif event.key == pygame.K_r:
                        do_restart()
                    elif event.key in (pygame.K_q, pygame.K_ESCAPE):
                        running = False
                continue  # ไม่ส่ง event ไปที่ scene

            # ── NORMAL PLAYING ────────────────────────────────────────────
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_p:
                    show_pause_menu = True
                    # อย่าส่ง event นี้เข้า scene เพื่อไม่ให้ scene pause ซ้ำ
                    continue
                elif event.key in (pygame.K_1, pygame.K_F1):
                    manager.switch_to("snowy", reset=True)
                    elapsed_since_switch = 0.0
                elif event.key in (pygame.K_2, pygame.K_F2):
                    manager.switch_to("hell", reset=True)
                    elapsed_since_switch = 0.0

            # ส่ง event ไปยัง scene ของเกม
            manager.handle_event(event)

        # ── auto-switch while playing ────────────────────────────────────────
        if (
            not show_game_over_menu
            and not show_title_screen
            and not show_howto_screen
            and not show_pause_menu
            and manager.current_name == "hell"
            and elapsed_since_switch >= SWITCH_INTERVAL
            and not transitioning
        ):
            print("[Timer] Auto-switching from HELL to SNOWY (with fade)")
            transitioning = True
            transition_alpha = 0
            transition_target = "snowy"
            transition_phase = 'out'

        # ── update & handle scene-requests ───────────────────────────────────
        if not (show_game_over_menu or show_title_screen or show_howto_screen or show_pause_menu):
            manager.update(dt)

            req = manager.shared.pop("_next_scene", None)
            if req and not manager.is_game_over():
                print(f"[SceneRequest] Scene requested switch to '{req}'")
                # If already transitioning, ignore; else do an immediate soft fade-in
                if not transitioning:
                    transitioning = True
                    transition_alpha = 0
                    transition_target = req
                    transition_phase = 'out'

        # ── draw base scene ─────────────────────────────────────────────────
        manager.draw()

        # ── overlay / UI screens ────────────────────────────────────────────
        if show_title_screen:
            title_scene.draw(screen)

        elif show_howto_screen:
            howto_scene.draw(screen)

        else:
            # HUD มุมซ้ายบน
            scene_name = manager.current_name.upper() if manager.current_name else "NONE"


            # แถวที่ 2: Hearts + Presents
            # --- HUD icon position depends on scene ---
            if manager.current_name == "hell":
                y = 80     # HELL → เลื่อนลงมามากขึ้น
            else:
                y = 50     # SNOWY → อยู่ตำแหน่งเดิม
                    
            spacing = 40

            # Hearts 3 ดวง
            hearts = manager.shared["hearts"]
            x = 10
            for i in range(3):
                if i < hearts:
                    screen.blit(heart_full, (x + i * spacing, y))
                else:
                    screen.blit(heart_empty, (x + i * spacing, y))

            # Presents icon + number
            px = x + 3 * spacing + 20
            screen.blit(present_img, (px, y))
            txt = small_font.render(str(manager.shared["presents"]), True, (255, 255, 255))
            screen.blit(txt, (px + ICON_SIZE + 6, y + 6))

            # Survival bar (เฉพาะใน HELL)
            if manager.current_name == "hell":
                bar_w, bar_h = 260, 20
                bar_x = (WIDTH // 2) - (bar_w // 2)
                bar_y = 10

                # ดึงเวลา Melt จาก HellScene (ถ้ามี)
                melt_left  = manager.shared.get("hell_melt_left")
                melt_total = manager.shared.get("hell_melt_total", SWITCH_INTERVAL)

                if melt_left is not None and melt_total > 0:
                    # ใช้อัตราส่วนเดียวกับที่แสดง Melt: X.Xs
                    ratio = melt_left / melt_total
                else:
                    # fallback กรณียังไม่ได้ส่งค่า shared
                    ratio = (SWITCH_INTERVAL - elapsed_since_switch) / SWITCH_INTERVAL

                ratio = max(0.0, min(1.0, ratio))

                # พื้นหลัง + กรอบ
                pygame.draw.rect(
                    screen,
                    (40, 40, 40),
                    pygame.Rect(bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4),
                    border_radius=8,
                )
                pygame.draw.rect(
                    screen,
                    (90, 90, 90),
                    pygame.Rect(bar_x, bar_y, bar_w, bar_h),
                    border_radius=6,
                )

                # แถบสีด้านใน
                inner_w = int(bar_w * ratio)
                if inner_w > 0:
                    pygame.draw.rect(
                        screen,
                        (255, 120, 80),
                        pygame.Rect(bar_x, bar_y, inner_w, bar_h),
                        border_radius=6,
                    )

                # label ตรงกลางบน bar
                label = small_font.render("HELL SURVIVAL", True, (255, 255, 255))
                label_rect = label.get_rect(center=(WIDTH // 2, bar_y - 18))
                screen.blit(label, label_rect)




            
            # Pause overlay
            if show_pause_menu:
                pause_scene.draw(screen)

            # Game Over overlay
            if show_game_over_menu:
                ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                ov.fill((0, 0, 0, 170))
                screen.blit(ov, (0, 0))

                title_font = pygame.font.SysFont("consolas", 72, bold=True)
                title = title_font.render("GAME OVER", True, (255, 240, 240))
                screen.blit(title, title.get_rect(center=(WIDTH//2, HEIGHT//2 - 120)))

                panel_w, panel_h = 520, 120
                panel_rect = pygame.Rect(0, 0, panel_w, panel_h)
                panel_rect.center = (WIDTH//2, HEIGHT//2 - 20)
                pygame.draw.rect(screen, (240, 240, 240), panel_rect, border_radius=16)
                pygame.draw.rect(screen, (60, 60, 60), panel_rect, 2, border_radius=16)

                big = pygame.font.SysFont("consolas", 36, bold=True)
                small = pygame.font.SysFont("consolas", 24)

                txt1 = big.render(f"Presents: {summary_presents}", True, (30, 30, 30))
                screen.blit(txt1, txt1.get_rect(midleft=(panel_rect.left + 30, panel_rect.centery - 20)))

                txt2 = small.render(f"Time Played: {fmt_mmss(summary_time_sec)}", True, (30, 30, 30))
                screen.blit(txt2, txt2.get_rect(midleft=(panel_rect.left + 30, panel_rect.centery + 24)))

                mouse_pos = pygame.mouse.get_pos()
                restart_btn.draw(screen, mouse_pos)
                quit_btn.draw(screen, mouse_pos)

                hint = pygame.font.SysFont("consolas", 18).render(
                    "Press R to Restart or Q to Quit", True, (235, 235, 235)
                )
                screen.blit(hint, hint.get_rect(center=(WIDTH//2, HEIGHT//2 + 170)))

        # Handle fade transition overlay and switching
        if transitioning:
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            if transition_phase == 'out':
                transition_alpha = min(255, transition_alpha + int(transition_speed * dt))
                ov.fill((0, 0, 0, max(0, min(255, transition_alpha))))
                screen.blit(ov, (0, 0))
                if transition_alpha >= 255 and transition_target:
                    manager.switch_to(transition_target, reset=True)
                    elapsed_since_switch = 0.0
                    transition_phase = 'in'
            elif transition_phase == 'in':
                transition_alpha = max(0, transition_alpha - int(transition_speed * dt))
                ov.fill((0, 0, 0, max(0, min(255, transition_alpha))))
                screen.blit(ov, (0, 0))
                if transition_alpha <= 0:
                    transitioning = False
                    transition_phase = None

        pygame.display.flip()
        clock.tick(FPS)

    # Cleanup (optional)
    for inst in list(manager.instances.values()):
        if hasattr(inst, "cleanup"):
            try:
                inst.cleanup()
            except Exception as e:
                print(f"[SceneManager] cleanup error: {e}")

    pygame.quit()


if __name__ == "__main__":
    main()
