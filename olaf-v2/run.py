from __future__ import annotations
import time
import pygame

# ── Window / timing ───────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1280, 720
FPS = 60
SWITCH_INTERVAL = 20.0   # seconds between automatic scene changes when playing
START_SCENE = "snowy"    # always begin & restart here

# ── Import scenes (package-relative) ──────────────────────────────────────────
from snowman.scenes.snowy import SnowyScene
from snowman.scenes.hell  import HellScene


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

    # Start from the beginning in Snowy
    manager.restart_to_start()

    running = True
    show_game_over_menu = False
    last_time = time.perf_counter()
    elapsed_since_switch = 0.0

    # Build menu buttons (positions are static)
    btn_w, btn_h = 240, 64
    spacing = 30
    cx, cy = WIDTH // 2, HEIGHT // 2 + 90

    def do_restart():
        nonlocal show_game_over_menu, elapsed_since_switch
        manager.restart_to_start()     # ALWAYS go to Snowy with fresh shared state + new timer
        show_game_over_menu = False    # close menu
        elapsed_since_switch = 0.0     # reset auto-switch timer

    def do_quit():
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    restart_btn = Button(pygame.Rect(cx - btn_w - spacing//2, cy, btn_w, btn_h),
                         "Restart (R)", do_restart)
    quit_btn    = Button(pygame.Rect(cx + spacing//2, cy, btn_w, btn_h),
                         "Quit (Q)",    do_quit)

    # Values captured at the moment of death for summary
    summary_time_sec = 0.0
    summary_label = "Presents"
    summary_count = 0

    while running:
        now = time.perf_counter()
        dt = now - last_time
        last_time = now

        # If not showing the menu, let the auto-switch timer advance; freeze while in menu
        if not show_game_over_menu:
            elapsed_since_switch += dt

        # Detect transition into game-over from the scene
        if not show_game_over_menu and manager.is_game_over():
            show_game_over_menu = True
            pygame.event.clear([pygame.KEYDOWN, pygame.KEYUP])
            # Snapshot summary
            summary_time_sec = manager.get_run_seconds()
            if manager.current_name == "hell":
                summary_label = "Ice"
                summary_count = manager.shared.get("ice", 0)
            else:
                summary_label = "Presents"
                summary_count = manager.shared.get("presents", 0)
            print("[UI] Game Over menu opened")

        # ── event handling ───────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if show_game_over_menu:
                        # ESC behaves like Quit on the menu
                        running = False
                    else:
                        running = False

                if show_game_over_menu:
                    if event.key in (pygame.K_r, pygame.K_RETURN):
                        do_restart()
                        continue
                    elif event.key in (pygame.K_q,):
                        running = False
                        continue
                else:
                    # Scene switching hotkeys only while playing
                    if event.key in (pygame.K_1, pygame.K_F1):
                        manager.switch_to("snowy", reset=True)
                        elapsed_since_switch = 0.0
                    elif event.key in (pygame.K_2, pygame.K_F2):
                        manager.switch_to("hell", reset=True)
                        elapsed_since_switch = 0.0

            # Route events to scene only when not in menu
            if not show_game_over_menu:
                manager.handle_event(event)
            else:
                restart_btn.handle_event(event)
                quit_btn.handle_event(event)

        # ── auto-switch while playing ────────────────────────────────────────
        if not show_game_over_menu and elapsed_since_switch >= SWITCH_INTERVAL:
            next_scene = "hell" if manager.current_name == "snowy" else "snowy"
            print(f"[Timer] Switching to {next_scene}")
            manager.switch_to(next_scene, reset=True)
            elapsed_since_switch = 0.0

        # ── update & draw scene ─────────────────────────────────────────────
        if not show_game_over_menu:
            manager.update(dt)
        manager.draw()

        # ── persistent HUD (top-left) while playing or menu ────────────────
        draw_overlay(
            screen,
            f"Scene: {manager.current_name.upper()} | Auto switch in {max(0.0, SWITCH_INTERVAL - elapsed_since_switch):.1f}s",
            10,
        )
        draw_overlay(
            screen,
            f"Hearts: {manager.shared['hearts']} | Presents: {manager.shared['presents']} | Ice: {manager.shared['ice']}",
            34,
        )
        draw_overlay(screen, "Esc=Quit | 1/F1 = Snowy | 2/F2 = Hell", 58)

        # ── Game Over menu overlay ──────────────────────────────────────────
        if show_game_over_menu:
            # dim background
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 170))
            screen.blit(ov, (0, 0))

            # title
            title_font = pygame.font.SysFont("consolas", 72, bold=True)
            title = title_font.render("GAME OVER", True, (255, 240, 240))
            screen.blit(title, title.get_rect(center=(WIDTH//2, HEIGHT//2 - 120)))

            # summary panel
            panel_w, panel_h = 520, 120
            panel_rect = pygame.Rect(0, 0, panel_w, panel_h)
            panel_rect.center = (WIDTH//2, HEIGHT//2 - 20)
            pygame.draw.rect(screen, (240, 240, 240), panel_rect, border_radius=16)
            pygame.draw.rect(screen, (60, 60, 60), panel_rect, 2, border_radius=16)

            big = pygame.font.SysFont("consolas", 36, bold=True)
            small = pygame.font.SysFont("consolas", 24)
            # Left: count
            txt1 = big.render(f"{summary_label}: {summary_count}", True, (30, 30, 30))
            screen.blit(txt1, txt1.get_rect(midleft=(panel_rect.left + 30, panel_rect.centery - 20)))
            # Right: time
            txt2 = small.render(f"Time Played: {fmt_mmss(summary_time_sec)}", True, (30, 30, 30))
            screen.blit(txt2, txt2.get_rect(midleft=(panel_rect.left + 30, panel_rect.centery + 24)))

            # buttons
            mouse_pos = pygame.mouse.get_pos()
            restart_btn.draw(screen, mouse_pos)
            quit_btn.draw(screen, mouse_pos)

            # hint
            hint = pygame.font.SysFont("consolas", 18).render(
                "Press R to Restart or Q to Quit", True, (235, 235, 235)
            )
            screen.blit(hint, hint.get_rect(center=(WIDTH//2, HEIGHT//2 + 170)))

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
