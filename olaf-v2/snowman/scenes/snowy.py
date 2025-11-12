from __future__ import annotations
import random
import pygame
import pygame.mixer
from pathlib import Path

# ── engine imports ────────────────────────────────────────────────────────────
try:
    from ..engine.spawner import Spawner, FallingSprite, load_image
except Exception:
    from snowman.engine.spawner import Spawner, FallingSprite, load_image  # fallback

# ── Config ────────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1280, 720
FPS = 60

BG_PATH = Path("image/background2.png")

CENTER_LANES_PCT = 0.86
PLAYABLE_CENTER_LANES = 3
PLAYER_TWEEN = 14.0
PLAYER_Y = int(HEIGHT * 0.78)
HORIZONTAL_SPREAD = 0.7

BG_SCROLL_SPEED_BASE = 400
BG_SCROLL_SPEED_MAX  = 1000
TIME_TO_MAX          = 60.0
SPEED_CURVE          = 0.6

OBSTACLE_PATHS = [Path("image/Tree_1.png"), Path("image/IceShards_1.png")]
PRESENT_PATH   = Path("image/Present_1.png")
SPECIAL_PATHS  = [Path("image/Moose_item_1.png"), Path("image/Carrot_1.png")]

PRESENT_SIZE  = 56
OBSTACLE_SIZE = 75
SPECIAL_SIZE  = 80
ASSET_SIZE_OVERRIDES = {"IceShards_1": 120, "Moose_item_1": 130}

OBSTACLE_SPEED = 260
PRESENT_SPEED  = 250
SPECIAL_SPEED  = 240

OBSTACLE_INTERVAL_RANGE = (0.8, 1.4)
PRESENT_INTERVAL_RANGE  = (0.45, 0.85)
SPECIAL_INTERVAL_RANGE  = (8.0, 14.0)

SPAWN_ACCEL_FACTOR = 0.55
OFFSCREEN_BUFFER   = 40
RELATIVE_SCROLL_MODE = True
RELATIVE_EXTRA_SPEED_FACTOR = 1.0

# ── Moose animation assets ────────────────────────────────────────────────────
MOOSE_RUN_1      = Path("image/Moose_run_1.png")
MOOSE_RUN_2      = Path("image/Moose_run_2.png")
MOOSE_TURN_LEFT  = Path("image/Moose_turn_left.png")
MOOSE_TURN_RIGHT = Path("image/Moose_turn_right.png")
MOOSE_SIZE       = 96     # visual size for moose frames
MOOSE_FPS        = 8.0    # run-cycle speed
MOOSE_TURN_TIME  = 0.18   # hold turn frame before resuming run

# ── Split-head effect assets ──────────────────────────────────────────────────
HEAD_PATHS_TRY = [Path("image/split/Head_1.png"), Path("image/split/Head_1 (1).png")]
HEAD_SIZE      = 56
HEAD_BOB_PIX   = 12
HEAD_FADE_OUT  = 0.35     # seconds to fade after carrot ends


# ── Scene class ───────────────────────────────────────────────────────────────
class SnowyScene:
    def set_shared(self, shared: dict):  # injected by SceneManager
        self.shared = shared

    # ---------- lifecycle ----------
    def start(self):
        if not hasattr(self, "shared"):
            self.shared = {"hearts": 3, "presents": 0, "ice": 0}  # safety

        self.font    = pygame.font.SysFont("Consolas", 20)
        self.bigfont = pygame.font.SysFont("Consolas", 44)

        self.bg_img = self._load_bg(BG_PATH) or pygame.Surface((WIDTH, HEIGHT))
        if not (self.bg_img.get_flags() & pygame.SRCALPHA):
            self.bg_img.fill((220, 235, 245))
        self.bg_offset = 0.0
        self.elapsed   = 0.0

        # lanes
        self.center_width = int(WIDTH * CENTER_LANES_PCT)
        self.outer_width  = (WIDTH - self.center_width) // 2
        self.lane_centers = []
        left_edge = self.outer_width
        for i in range(PLAYABLE_CENTER_LANES):
            frac = (2 * i + 1) / (2 * PLAYABLE_CENTER_LANES)
            cx = left_edge + int(self.center_width * frac)
            self.lane_centers.append(cx)

        def adjusted_lane_x(idx: int) -> int:
            if PLAYABLE_CENTER_LANES != 3:
                return self.lane_centers[idx]
            mid_x = self.lane_centers[1]
            if idx == 1:
                return mid_x
            edge_x = self.lane_centers[idx]
            return int(mid_x + (edge_x - mid_x) * HORIZONTAL_SPREAD)

        self.adjusted_lane_x = adjusted_lane_x

        # groups
        self.all_sprites = pygame.sprite.Group()
        self.fx_sprites  = pygame.sprite.Group()  # transient effects (split heads)

        # player
        self.player = _Player(self.adjusted_lane_x, start_lane=1)
        self.all_sprites.add(self.player)

        # spawner
        self.spawner = Spawner(
            lane_centers=self.lane_centers,
            adjusted_lane_x=self.adjusted_lane_x,
            all_sprites=self.all_sprites,
            obstacle_paths=OBSTACLE_PATHS,
            present_path=PRESENT_PATH,
            special_paths=SPECIAL_PATHS,
            present_size=PRESENT_SIZE,
            obstacle_size=OBSTACLE_SIZE,
            special_size=SPECIAL_SIZE,
            size_overrides=ASSET_SIZE_OVERRIDES,
            obstacle_speed=OBSTACLE_SPEED,
            present_speed=PRESENT_SPEED,
            special_speed=SPECIAL_SPEED,
            obstacle_interval=OBSTACLE_INTERVAL_RANGE,
            present_interval=PRESENT_INTERVAL_RANGE,
            special_interval=SPECIAL_INTERVAL_RANGE,
            spawn_accel_factor=SPAWN_ACCEL_FACTOR,
            base_speed=BG_SCROLL_SPEED_BASE,
            max_speed=BG_SCROLL_SPEED_MAX,
            offscreen_buffer=OFFSCREEN_BUFFER,
            relative_scroll_mode=RELATIVE_SCROLL_MODE,
            relative_extra_factor=RELATIVE_EXTRA_SPEED_FACTOR,
            present_score_value=1,
            special_score_bonus=5,
        )

        # ── Sound: init + load ───────────────────────────────────────────────
        if pygame.mixer.get_init() is None:
            try:
                pygame.mixer.init()
            except Exception as e:
                print(f"[Sound] Mixer init failed: {e}")

        try:
            pygame.mixer.music.load("sound/snowy_bm.mp3")
            pygame.mixer.music.set_volume(0.55)
            pygame.mixer.music.play(-1)
        except Exception as e:
            print(f"[Sound] Music load/play failed: {e}")

        self.sounds = {}
        def _safe_sound(name, path, vol=1.0):
            try:
                s = pygame.mixer.Sound(path)
                s.set_volume(vol)
                self.sounds[name] = s
            except Exception as e:
                print(f"[Sound] Failed to load {path}: {e}")
                self.sounds[name] = None

        _safe_sound("present", "sound/present_collected.wav", 0.9)
        _safe_sound("special", "sound/item_collected.wav",    0.9)
        _safe_sound("hit",     "sound/obstacles_hit.wav",     0.9)
        _safe_sound("fail",    "sound/failing.wav",           0.9)

        # ── Moose frames ────────────────────────────────────────────────────
        self.player.load_moose_frames(
            run_paths=[MOOSE_RUN_1, MOOSE_RUN_2],
            left_path=MOOSE_TURN_LEFT,
            right_path=MOOSE_TURN_RIGHT,
            size=MOOSE_SIZE
        )

        # Preload split-head image
        self.head_image = self._load_first_ok(HEAD_PATHS_TRY, HEAD_SIZE)

        # Active heads (persist through the carrot phase)
        self.carrot_heads: list[_LaneHead] = []

        # scene-local state
        self.state = {
            "slow_timer": 0.0,
            "hit_flash": 0.0,
            "pickup_flash": 0.0,
            "phase_kind": None,
            "phase_timer": 0.0,
            "phase_start_flash": 0.0,
            "frame_collected_presents": 0,
            "frame_collected_specials": [],
            "active_buff": None,
        }

        self.show_start = False
        self.paused = False
        self.game_over = False
        self._played_game_over_snd = False

    def reset(self):
        # stop scene music
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

        # clear spawner sprites
        if hasattr(self, "spawner"):
            for g in (self.spawner.obstacles, self.spawner.collectibles, self.spawner.special_items):
                for s in list(g): s.kill()

        # clear effect sprites
        for s in list(self.fx_sprites):
            s.kill()
        self.carrot_heads.clear()

        # timers/state
        self.bg_offset = 0.0
        self.elapsed = 0.0
        self.state.update({
            "slow_timer": 0.0, "hit_flash": 0.0, "pickup_flash": 0.0,
            "phase_kind": None, "phase_timer": 0.0, "phase_start_flash": 0.0,
            "frame_collected_presents": 0, "frame_collected_specials": [], "active_buff": None,
        })
        self.show_start = False
        self.paused = False
        self.game_over = False
        self._played_game_over_snd = False

        # player back to normal sprite
        self.player.set_mode("normal")

        # restart music
        try:
            pygame.mixer.music.load("sound/snowy_bm.mp3")
            pygame.mixer.music.set_volume(0.55)
            pygame.mixer.music.play(-1)
        except Exception:
            pass

    # ---------- input/update/draw ----------
    def handle_event(self, ev: pygame.event.Event):
        if ev.type == pygame.KEYDOWN and not (self.paused or self.game_over):
            if ev.key in (pygame.K_LEFT, pygame.K_a):
                self.player.move_left()
            elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                self.player.move_right()
            elif ev.key == pygame.K_p:
                self.paused = not self.paused

    def update(self, dt: float):
        if self.paused or self.game_over:
            return

        # timers
        for k in ("slow_timer", "hit_flash", "pickup_flash", "phase_timer", "phase_start_flash"):
            if self.state.get(k, 0.0) > 0.0:
                self.state[k] = max(0.0, self.state[k] - dt)
                if k == "phase_timer" and self.state["phase_timer"] == 0.0:
                    # on phase end: revert looks & fade heads if needed
                    if self.state.get("phase_kind") == "moose":
                        self.player.set_mode("normal")
                    if self.state.get("phase_kind") == "carrot" and self.carrot_heads:
                        for h in self.carrot_heads:
                            h.begin_fade_out()
                        self.carrot_heads.clear()
                    self.state["phase_kind"] = None
                    self.state["active_buff"] = None

        # speed model
        self.elapsed += dt
        portion = min(1.0, self.elapsed / max(0.001, TIME_TO_MAX))
        base_speed = BG_SCROLL_SPEED_BASE + (BG_SCROLL_SPEED_MAX - BG_SCROLL_SPEED_BASE) * (portion ** SPEED_CURVE)
        speed_mult = 0.6 if self.state["slow_timer"] > 0.0 else 1.0
        if self.state["phase_timer"] > 0.0:
            speed_mult *= 1.9
        current_speed = base_speed * speed_mult
        self.bg_offset -= current_speed * dt

        # spawn/update
        self.spawner.update(dt, current_speed)
        for spr in list(self.all_sprites):
            if isinstance(spr, FallingSprite):
                spr.update(dt, current_speed)
            else:
                spr.update(dt)
        for fx in list(self.fx_sprites):
            fx.update(dt)

        # collisions (skip when phased)
        if self.state["phase_timer"] <= 0.0:
            self.spawner.handle_collisions(self.player, self.state)

            # presents
            picked = self.state.get("frame_collected_presents", 0)
            if picked > 0:
                self.shared["presents"] += picked
                self.state["pickup_flash"] = max(self.state["pickup_flash"], 0.12)
                if self.sounds.get("present"): self.sounds["present"].play()

            # specials
            specials = [n.lower() for n in self.state.get("frame_collected_specials", [])]
            if specials:
                if any(("carrot" in n) for n in specials):
                    self.state["phase_kind"] = "carrot"
                    self.state["phase_timer"] = 2.0
                    self.state["phase_start_flash"] = 0.25
                    self._spawn_heads_on_lanes()   # keep heads for entire carrot effect
                if any(("moose" in n) for n in specials):
                    self.state["phase_kind"] = "moose"
                    self.state["phase_timer"] = 2.0
                    self.state["phase_start_flash"] = 0.25
                    self.player.set_mode("moose")
                if self.sounds.get("special"): self.sounds["special"].play()

            # obstacle hits
            collide_fn = pygame.sprite.collide_circle_ratio(1.05)
            for ob in list(self.spawner.obstacles):
                if collide_fn(self.player, ob):
                    self.shared["hearts"] = max(0, self.shared["hearts"] - 1)
                    self.state["slow_timer"]  = max(self.state["slow_timer"], 1.0)
                    self.state["hit_flash"]   = max(self.state["hit_flash"], 0.25)
                    ob.kill()
                    if self.sounds.get("hit"): self.sounds["hit"].play()

        # game over?
        if self.shared["hearts"] <= 0:
            self.game_over = True

        self._current_speed_dbg = current_speed  # debug HUD

    def draw(self, screen: pygame.Surface):
        self._draw_bg(screen)

        # world
        self.all_sprites.draw(screen)
        self.fx_sprites.draw(screen)

        # force player on top of everything
        screen.blit(self.player.image, self.player.rect)

        # HUD
        y = 8
        screen.blit(self.font.render("SNOWY", True, (30, 30, 30)), (10, y)); y += 22
        screen.blit(self.font.render(f"Hearts: {self.shared['hearts']}", True, (220,70,70)), (10, y)); y += 22
        screen.blit(self.font.render(f"Presents: {self.shared['presents']}", True, (60,120,200)), (10, y)); y += 22
        screen.blit(self.font.render(f"Speed: {int(getattr(self, '_current_speed_dbg', 0))} px/s", True, (40,40,40)), (10, y))

        if self.game_over:
            if not self._played_game_over_snd:
                try:
                    pygame.mixer.music.fadeout(400)
                except Exception:
                    pass
                if self.sounds.get("fail"):
                    self.sounds["fail"].play()
                self._played_game_over_snd = True

            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); ov.fill((0, 0, 0, 150))
            screen.blit(ov, (0, 0))
            t = self.bigfont.render("GAME OVER", True, (255, 220, 220))
            screen.blit(t, t.get_rect(center=(WIDTH//2, HEIGHT//2)))

    # ---------- helpers ----------
    def _load_bg(self, path: Path) -> pygame.Surface | None:
        try:
            img = pygame.image.load(str(path)).convert_alpha()
        except Exception:
            return None
        iw, ih = img.get_size()
        scale = WIDTH / iw
        return pygame.transform.smoothscale(img, (WIDTH, max(HEIGHT, int(ih * scale))))

    def _load_first_ok(self, paths: list[Path], size: int) -> pygame.Surface | None:
        for p in paths:
            try:
                img = pygame.image.load(str(p)).convert_alpha()
                return pygame.transform.smoothscale(img, (size, size))
            except Exception:
                continue
        print("[Split] Head image not found; effect disabled.")
        return None

    def _draw_bg(self, surf: pygame.Surface):
        img = self.bg_img
        h = img.get_height()
        y = -int(self.bg_offset % h)
        surf.blit(img, (0, y))
        surf.blit(img, (0, y + h))
        if y + h < HEIGHT:
            surf.blit(img, (0, y + h * 2))

    def _spawn_heads_on_lanes(self):
        """Spawn (or refresh) one head above each lane; persists for carrot phase."""
        if self.head_image is None:
            return

        # Already present (e.g., carrot picked again) → refresh visuals
        if self.carrot_heads:
            for h in self.carrot_heads:
                h.refresh_for_phase()
            return

        y = PLAYER_Y - 110
        self.carrot_heads = []
        for cx in self.lane_centers:
            spr = _LaneHead(self, self.head_image, (int(cx), y))
            self.fx_sprites.add(spr)          # <- only in FX group (not all_sprites)
            self.carrot_heads.append(spr)


class _LaneHead(pygame.sprite.Sprite):
    """
    Head effect shown on carrot pickup.
    Stays fully visible during the carrot phase; fades out during the last
    HEAD_FADE_OUT seconds or when begin_fade_out() is called.
    """
    def __init__(self, scene: SnowyScene, img: pygame.Surface, center: tuple[int, int]):
        super().__init__()
        self.scene = scene
        self.base_image = img
        self.image = img.copy()
        self.rect = self.image.get_rect(center=center)

        self.t = 0.0               # time for bobbing
        self.base_center = center  # remember original center (no drift)
        self.manual_fade = False
        self.fade_elapsed = 0.0

    def refresh_for_phase(self):
        self.manual_fade = False
        self.fade_elapsed = 0.0
        self.image = self.base_image.copy()

    def begin_fade_out(self):
        self.manual_fade = True
        self.fade_elapsed = 0.0

    def update(self, dt: float):
        import math
        self.t += dt
        bob = int(math.sin(self.t * 10.0) * HEAD_BOB_PIX * 0.6)
        self.rect.center = (self.base_center[0], self.base_center[1] + bob)

        # Compute alpha
        alpha = 255
        if self.manual_fade:
            self.fade_elapsed += dt
            if self.fade_elapsed >= HEAD_FADE_OUT:
                self.kill()
                return
            alpha = max(0, int(255 * (1.0 - self.fade_elapsed / HEAD_FADE_OUT)))
        else:
            if self.scene.state.get("phase_kind") == "carrot":
                rem = max(0.0, float(self.scene.state.get("phase_timer", 0.0)))
                if rem <= 0.0:
                    self.begin_fade_out()
                    return
                if HEAD_FADE_OUT > 0.0 and rem < HEAD_FADE_OUT:
                    alpha = max(0, int(255 * (rem / HEAD_FADE_OUT)))
            else:
                self.begin_fade_out()
                return

        # Apply alpha
        self.image = self.base_image.copy()
        self.image.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)


class _Player(pygame.sprite.Sprite):
    def __init__(self, adjusted_lane_x, start_lane=1):
        super().__init__()
        # Try to use Snowman_idle2.png; fallback to a drawn circle
        self.normal_image = self._load_or_make_normal()
        self.image = self.normal_image.copy()
        self.rect = self.image.get_rect(center=(adjusted_lane_x(start_lane), PLAYER_Y))

        self.lane = start_lane
        self.target_x = float(self.rect.centerx)
        self.speed_tween = PLAYER_TWEEN
        self._adjusted_lane_x = adjusted_lane_x
        self.radius = int(self.image.get_width() * 0.45)

        # animation state
        self.mode = "normal"   # "normal" or "moose"
        self.moose_frames_run = []
        self.moose_frame_left = None
        self.moose_frame_right = None
        self.anim_idx = 0
        self.anim_timer = 0.0
        self.turn_timer = 0.0
        self.turn_dir = None

    # --- external API ---
    def load_moose_frames(self, run_paths, left_path, right_path, size=MOOSE_SIZE):
        def _ld(p: Path):
            try:
                img = pygame.image.load(str(p)).convert_alpha()
                return pygame.transform.smoothscale(img, (size, size))
            except Exception as e:
                print(f"[Moose] Failed to load {p}: {e}")
                return None

        self.moose_frames_run = [f for f in (_ld(run_paths[0]), _ld(run_paths[1])) if f is not None]
        self.moose_frame_left = _ld(left_path)
        self.moose_frame_right = _ld(right_path)

    def set_mode(self, mode: str):
        if mode == self.mode:
            return
        self.mode = mode
        self.anim_idx = 0
        self.anim_timer = 0.0
        self.turn_timer = 0.0
        if self.mode == "normal":
            self.image = self.normal_image.copy()
            self._reset_rect_center()
        elif self.mode == "moose":
            if len(self.moose_frames_run) < 2 or self.moose_frame_left is None or self.moose_frame_right is None:
                self.mode = "normal"
                self.image = self.normal_image.copy()
            else:
                self.image = self.moose_frames_run[0]
            self._reset_rect_center()

    # --- movement / animation ---
    def update(self, dt):
        # tween to target lane position
        dx = self.target_x - self.rect.centerx
        step = dx * min(1.0, self.speed_tween * dt)
        self.rect.centerx += step

        # animate if in moose mode
        if self.mode == "moose":
            if self.turn_timer > 0.0:
                self.turn_timer = max(0.0, self.turn_timer - dt)
            else:
                self.anim_timer += dt
                if self.anim_timer >= (1.0 / MOOSE_FPS):
                    self.anim_timer = 0.0
                    self.anim_idx = (self.anim_idx + 1) % 2
                    self.image = self.moose_frames_run[self.anim_idx]
        else:
            self.image = self.normal_image

    def move_left(self):
        self.lane = max(0, self.lane - 1)
        self.target_x = self._adjusted_lane_x(self.lane)
        if self.mode == "moose" and self.moose_frame_left is not None:
            self.image = self.moose_frame_left
            self.turn_dir = "left"
            self.turn_timer = MOOSE_TURN_TIME

    def move_right(self):
        self.lane = min(PLAYABLE_CENTER_LANES - 1, self.lane + 1)
        self.target_x = self._adjusted_lane_x(self.lane)
        if self.mode == "moose" and self.moose_frame_right is not None:
            self.image = self.moose_frame_right
            self.turn_dir = "right"
            self.turn_timer = MOOSE_TURN_TIME

    def _reset_rect_center(self):
        c = self.rect.center
        self.rect = self.image.get_rect(center=c)

    def _load_or_make_normal(self) -> pygame.Surface:
        try:
            img = pygame.image.load("image/Snowman_idle2.png").convert_alpha()
            return pygame.transform.smoothscale(img, (64, 64))
        except Exception:
            # fallback: draw a simple snowman head
            size = 64
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(surf, (245, 245, 255), (size//2, size//2), size//2)
            pygame.draw.circle(surf, (200, 200, 200), (size//2, size//2+6), size//2-6, 3)
            return surf
