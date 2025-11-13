# snowman/scenes/snowy.py
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

# ── Igloo/minigames ──────────────────────────────────────────────────────────
IGLOO_PATH = Path("image/Igloo_2.png")
IGLOO_SIZE = 90
IGLOO_INTERVAL_RANGE = (7.0, 14.0)

IGLOO_TRIGGER_TIME   = 50.0  # time until first igloo calm-zone starts
IGLOO_GAP_BEFORE     = 2.0   # 2 seconds of no items before igloos spawn

# ── Moose animation assets ────────────────────────────────────────────────────
MOOSE_RUN_1      = Path("image/Moose_run_1.png")
MOOSE_RUN_2      = Path("image/Moose_run_2.png")
MOOSE_TURN_LEFT  = Path("image/Moose_turn_left.png")
MOOSE_TURN_RIGHT = Path("image/Moose_turn_right.png")
MOOSE_SIZE       = 96
MOOSE_FPS        = 8.0
MOOSE_TURN_TIME  = 0.18

# ── Split-body assets (for carrot power) ─────────────────────────────────────
HEAD_PATHS_TRY = [Path("image/split/Head_1.png"), Path("image/split/Head_1 (1).png")]
UPPER_PATH     = Path("image/split/UpperBody_1.png")
LOWER_PATH     = Path("image/split/LowerBody_1.png")
HEAD_SIZE      = 56
HEAD_BOB_PIX   = 12
HEAD_FADE_OUT  = 0.35


# ── Igloo falling item ────────────────────────────────────────────────────────
class IglooItem(FallingSprite):
    def __init__(self, lane_index, adjusted_lane_x, speed):
        img = load_image(IGLOO_PATH, IGLOO_SIZE)
        super().__init__(
            img, lane_index, speed, adjusted_lane_x,
            offscreen_buffer=OFFSCREEN_BUFFER,
            relative_scroll_mode=True, relative_extra_factor=1.0,
        )
        self.radius = max(self.rect.width, self.rect.height) // 2 + 6
        # game_cls will be attached later when spawning


# ── Minigame #1: Tic-Tac-Toe (XO) ────────────────────────────────────────────
class _TicTacToe:
    def __init__(self):
        self.grid = [['' for _ in range(3)] for _ in range(3)]
        self.turn = 'X'
        self.cell = 120
        self.margin_y = 140
        self.done = False
        self.win = False
        self.result_text = "Click in the grid to place X"

    def handle_event(self, e):
        if self.done:
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.turn == 'X':
            mx, my = e.pos
            gx = (WIDTH - 3*self.cell)//2
            gy = self.margin_y
            if gx <= mx < gx+3*self.cell and gy <= my < gy+3*self.cell:
                c = (mx - gx)//self.cell
                r = (my - gy)//self.cell
                r, c = int(r), int(c)
                if self.grid[r][c] == '':
                    self.grid[r][c] = 'X'
                    self._post_move()

    def draw(self, screen, font, bigfont):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,160))
        screen.blit(overlay, (0,0))

        title = bigfont.render("IGLOO MINI-GAME: XO", True, (255, 255, 220))
        screen.blit(title, title.get_rect(center=(WIDTH//2, 80)))

        gx = (WIDTH - 3*self.cell)//2
        gy = self.margin_y
        for i in range(4):
            x = gx + i*self.cell
            y = gy + i*self.cell
            pygame.draw.line(screen, (240,240,240), (gx, y), (gx+3*self.cell, y), 2)
            pygame.draw.line(screen, (240,240,240), (x, gy), (x, gy+3*self.cell), 2)
        for r in range(3):
            for c in range(3):
                cx = gx + c*self.cell + self.cell//2
                cy = gy + r*self.cell + self.cell//2
                mark = self.grid[r][c]
                if mark == 'X':
                    pygame.draw.line(screen, (255,200,160), (cx-30, cy-30), (cx+30, cy+30), 6)
                    pygame.draw.line(screen, (255,200,160), (cx+30, cy-30), (cx-30, cy+30), 6)
                elif mark == 'O':
                    pygame.draw.circle(screen, (160,220,255), (cx, cy), 34, 6)

        tip = font.render(self.result_text + ("  (Click to close)" if self.done else ""), True, (255, 255, 255))
        screen.blit(tip, tip.get_rect(center=(WIDTH//2, HEIGHT-80)))

    def _post_move(self):
        w = self._winner()
        if w or self._full():
            self._finish(w)
        else:
            self.turn = 'O'
            empties = [(r,c) for r in range(3) for c in range(3) if self.grid[r][c] == '']
            if empties:
                r, c = random.choice(empties)
                self.grid[r][c] = 'O'
            w = self._winner()
            if w or self._full():
                self._finish(w)
            else:
                self.turn = 'X'

    def _full(self):
        return all(self.grid[r][c] != '' for r in range(3) for c in range(3))

    def _winner(self):
        g = self.grid
        lines = g + [[g[0][i], g[1][i], g[2][i]] for i in range(3)]
        lines += [[g[0][0], g[1][1], g[2][2]], [g[0][2], g[1][1], g[2][0]]]
        for line in lines:
            if line[0] and line[0] == line[1] == line[2]:
                return line[0]
        return None

    def _finish(self, winner):
        self.done = True
        if winner == 'X':
            self.win = True
            self.result_text = "You WIN! Reward: +10 Presents"
        elif winner == 'O':
            self.win = False
            self.result_text = "You LOSE! Consolation: +0 Presents"
        else:
            self.win = False
            self.result_text = "DRAW! Consolation: +0 Presents"


# ── Minigame #2: Memory Flip ─────────────────────────────────────────────────
class _MemoryFlip:
    """
    Flip two cards to find a matching pair. Match all pairs before time runs out.
    """
    def __init__(self):
        self.cols, self.rows = 3, 2               # 2×3 grid → 3 pairs
        pairs = list(range(1, (self.cols*self.rows)//2 + 1)) * 2
        random.shuffle(pairs)

        self.card_w, self.card_h = 120, 140
        total_w = self.cols * self.card_w + (self.cols - 1) * 14
        total_h = self.rows * self.card_h + (self.rows - 1) * 14
        self.board_left = (WIDTH - total_w) // 2
        self.board_top  = 170

        self.cards = []
        k = 0
        for r in range(self.rows):
            for c in range(self.cols):
                x = self.board_left + c * (self.card_w + 14)
                y = self.board_top  + r * (self.card_h + 14)
                self.cards.append({
                    "rect": pygame.Rect(x, y, self.card_w, self.card_h),
                    "value": pairs[k],
                    "revealed": False,
                    "matched": False
                })
                k += 1

        self.first_idx = None
        self.lock_input = False
        self.mismatch_timer = 0.0

        self.time_limit = 25.0
        self.time_left = self.time_limit
        self.done = False
        self.win = False
        self.result_text = "Flip cards and match all pairs!"

    def update(self, dt):
        if self.done:
            return

        self.time_left = max(0.0, self.time_left - dt)
        if self.time_left <= 0.0:
            self._finish(False, "Time up! +0 Presents")
            return

        if self.lock_input:
            self.mismatch_timer -= dt
            if self.mismatch_timer <= 0:
                self.lock_input = False
                to_hide = [i for i, c in enumerate(self.cards) if c.get("_temp_reveal")]
                for i in to_hide:
                    self.cards[i]["revealed"] = False
                    self.cards[i]["_temp_reveal"] = False

        if all(c["matched"] for c in self.cards):
            self._finish(True, "All matched! +10 Presents")

    def handle_event(self, e):
        if self.done or self.lock_input:
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            mx, my = e.pos
            for i, card in enumerate(self.cards):
                if card["rect"].collidepoint(mx, my) and not card["matched"] and not card["revealed"]:
                    self._flip(i)
                    break

    def draw(self, screen, font, bigfont):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,160))
        screen.blit(overlay, (0,0))

        title = bigfont.render("IGLOO MINI-GAME: MEMORY FLIP", True, (255, 255, 220))
        screen.blit(title, title.get_rect(center=(WIDTH//2, 100)))

        bar_w = int((self.time_left / self.time_limit) * 520)
        pygame.draw.rect(screen, (255,255,255), (WIDTH//2 - 260, 140, 520, 14), 2)
        pygame.draw.rect(screen, (190,240,210), (WIDTH//2 - 260, 140, bar_w, 14))

        for card in self.cards:
            r = card["rect"]
            if card["matched"]:
                pygame.draw.rect(screen, (120, 200, 150), r, border_radius=12)
                v = bigfont.render(str(card["value"]), True, (20,40,30))
                screen.blit(v, v.get_rect(center=r.center))
            elif card["revealed"]:
                pygame.draw.rect(screen, (230, 230, 255), r, border_radius=12)
                pygame.draw.rect(screen, (255,255,255), r, 3, border_radius=12)
                v = bigfont.render(str(card["value"]), True, (40,50,120))
                screen.blit(v, v.get_rect(center=r.center))
            else:
                pygame.draw.rect(screen, (60, 90, 130), r, border_radius=12)
                pygame.draw.rect(screen, (255,255,255), r, 3, border_radius=12)
                cx, cy = r.center
                pygame.draw.line(screen, (255,255,255), (cx-18, cy), (cx+18, cy), 3)
                pygame.draw.line(screen, (255,255,255), (cx, cy-18), (cx, cy+18), 3)
                pygame.draw.line(screen, (255,255,255), (cx-13, cy-13), (cx+13, cy+13), 3)
                pygame.draw.line(screen, (255,255,255), (cx-13, cy+13), (cx+13, cy-13), 3)

        tip = font.render(self.result_text + ("  (Click to close)" if self.done else ""), True, (255,255,255))
        screen.blit(tip, tip.get_rect(center=(WIDTH//2, HEIGHT-70)))

    def _flip(self, idx):
        card = self.cards[idx]
        card["revealed"] = True
        if self.first_idx is None:
            self.first_idx = idx
            return

        a = self.cards[self.first_idx]
        b = card
        if a["value"] == b["value"]:
            a["matched"] = True
            b["matched"] = True
            self.first_idx = None
            self.result_text = "Nice! Keep going!"
        else:
            a["_temp_reveal"] = True
            b["_temp_reveal"] = True
            self.lock_input = True
            self.mismatch_timer = 0.7
            self.first_idx = None

    def _finish(self, win, msg):
        self.done = True
        self.win = win
        self.result_text = msg


# ── Minigame #3: Quick Math ──────────────────────────────────────────────────
class _QuickMath:
    """
    Type the correct answer and press Enter before time runs out.
    """
    def __init__(self):
        a = random.randint(4, 19)
        b = random.randint(3, 17)
        if random.random() < 0.5 and a > b:
            self.op = '-'
            self.a, self.b = a, b
            self.ans = a - b
        else:
            self.op = '+'
            self.a, self.b = a, b
            self.ans = a + b

        self.buf = ""
        self.time_limit = 7.0
        self.time_left = self.time_limit
        self.done = False
        self.win = False
        self.result_text = "Type your answer and press Enter"

    def update(self, dt):
        if self.done:
            return
        self.time_left = max(0.0, self.time_left - dt)
        if self.time_left <= 0.0:
            self._finish(False, f"Time up! Answer: {self.ans}")

    def handle_event(self, e):
        if self.done:
            return
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_RETURN:
                try:
                    ok = (int(self.buf) == self.ans)
                except Exception:
                    ok = False
                if ok:
                    self._finish(True, "Correct! +10 Presents")
                else:
                    self._finish(False, f"Wrong! Answer: {self.ans}")
            elif e.key == pygame.K_BACKSPACE:
                self.buf = self.buf[:-1]
            else:
                ch = e.unicode
                if ch.isdigit() or (ch == '-' and len(self.buf) == 0):
                    if len(self.buf) < 6:
                        self.buf += ch

    def draw(self, screen, font, bigfont):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,160))
        screen.blit(overlay, (0,0))

        title = bigfont.render("IGLOO MINI-GAME: QUICK MATH", True, (255, 255, 220))
        screen.blit(title, title.get_rect(center=(WIDTH//2, 80)))

        q = bigfont.render(f"{self.a} {self.op} {self.b} = ?", True, (255,255,255))
        screen.blit(q, q.get_rect(center=(WIDTH//2, HEIGHT//2 - 20)))

        ans = bigfont.render(self.buf if self.buf else "_", True, (200,255,220))
        screen.blit(ans, ans.get_rect(center=(WIDTH//2, HEIGHT//2 + 60)))

        bar_w = int((self.time_left / self.time_limit) * 500)
        pygame.draw.rect(screen, (255,255,255), (WIDTH//2 - 250, HEIGHT - 130, 500, 16), 2)
        pygame.draw.rect(screen, (180,240,200), (WIDTH//2 - 250, HEIGHT - 130, bar_w, 16))

        tip = font.render(self.result_text + ("  (Click to close)" if self.done else ""), True, (255,255,255))
        screen.blit(tip, tip.get_rect(center=(WIDTH//2, HEIGHT-80)))

    def _finish(self, win, msg):
        self.done = True
        self.win = win
        self.result_text = msg


# ── Scene class ───────────────────────────────────────────────────────────────
class SnowyScene:
    def set_shared(self, shared: dict):
        self.shared = shared

    # ---------- lifecycle ----------
    def start(self):
        if not hasattr(self, "shared"):
            self.shared = {"hearts": 3, "presents": 0, "ice": 0}

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
        self.fx_sprites  = pygame.sprite.Group()
        self.igloos      = pygame.sprite.Group()

        # player (NOT in all_sprites – drawn manually so we can hide him)
        self.player = _Player(self.adjusted_lane_x, start_lane=1)

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

        # ── Sound init ───────────────────────────────────────────────────────
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

        # moose frames
        self.player.load_moose_frames(
            run_paths=[MOOSE_RUN_1, MOOSE_RUN_2],
            left_path=MOOSE_TURN_LEFT,
            right_path=MOOSE_TURN_RIGHT,
            size=MOOSE_SIZE
        )

        # split-body preload (head / upper / lower)
        self.split_images = self._load_split_images(HEAD_SIZE)
        self.carrot_parts: list[_SplitPart] = []

        # scene state
        self.state = {
            "slow_timer": 0.0, "hit_flash": 0.0, "pickup_flash": 0.0,
            "phase_kind": None, "phase_timer": 0.0, "phase_start_flash": 0.0,
            "frame_collected_presents": 0, "frame_collected_specials": [],
            "active_buff": None,
        }

        self.show_start = False
        self.paused = False
        self.game_over = False
        self._played_game_over_snd = False

        # minigames (each igloo lane → its own game)
        self.in_minigame = False
        self.mini = None
        self.mini_kinds = [_TicTacToe, _MemoryFlip, _QuickMath]

        # Igloo timing:
        self.next_igloo_t = IGLOO_TRIGGER_TIME   # countdown until calm-zone start
        self.pre_igloo_gap = 0.0                # 2s window with no items

        # carrot effect flags
        self.player_hidden   = False   # hide main snowman while split
        self.post_carrot_gap = 0.0     # 1 second of no spawns after effect

    def reset(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

        if hasattr(self, "spawner"):
            for g in (self.spawner.obstacles, self.spawner.collectibles, self.spawner.special_items):
                for s in list(g):
                    s.kill()

        for s in list(self.igloos):
            s.kill()
        for s in list(self.fx_sprites):
            s.kill()
        self.igloos.empty()
        self.fx_sprites.empty()
        self.carrot_parts.clear()

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
        self.player.set_mode("normal")

        self.in_minigame = False
        self.mini = None

        self.next_igloo_t = IGLOO_TRIGGER_TIME
        self.pre_igloo_gap = 0.0

        self.player_hidden   = False
        self.post_carrot_gap = 0.0

        try:
            pygame.mixer.music.load("sound/snowy_bm.mp3")
            pygame.mixer.music.set_volume(0.55)
            pygame.mixer.music.play(-1)
        except Exception:
            pass

    # ---------- input/update/draw ----------
    def handle_event(self, ev: pygame.event.Event):
        # Minigame has priority
        if self.in_minigame and self.mini:
            if hasattr(self.mini, "handle_event"):
                self.mini.handle_event(ev)
            # close overlay on click after done; apply reward
            if ev.type == pygame.MOUSEBUTTONDOWN and self.mini.done:
                did_win = getattr(self.mini, "win", False)
                if did_win:
                    self.shared["presents"] += 10
                    # request scene change to HELL after finishing igloo minigame
                    self.shared["_next_scene"] = "hell"
                self.in_minigame = False
                self.mini = None
            return

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

        # While in minigame, freeze world but let minigame update timers
        if self.in_minigame and self.mini:
            if hasattr(self.mini, "update"):
                self.mini.update(dt)
            return

        # timers
        for k in ("slow_timer", "hit_flash", "pickup_flash", "phase_timer", "phase_start_flash"):
            if self.state.get(k, 0.0) > 0.0:
                self.state[k] = max(0.0, self.state[k] - dt)
                if k == "phase_timer" and self.state["phase_timer"] == 0.0:
                    if self.state.get("phase_kind") == "moose":
                        self.player.set_mode("normal")
                    if self.state.get("phase_kind") == "carrot" and self.carrot_parts:
                        for h in self.carrot_parts:
                            h.begin_fade_out()
                        self.carrot_parts.clear()
                        self.player_hidden   = False
                        self.post_carrot_gap = 2.0   # 1 second no items after split ends
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

        # ---------- Igloo timing + gap logic ----------
        # Only care if no igloos on-screen and not inside minigame
        if len(self.igloos) == 0 and not self.in_minigame:
            if self.next_igloo_t > 0.0:
                self.next_igloo_t -= dt
                if self.next_igloo_t <= 0.0:
                    # start 2-second calm zone: clear existing items
                    self.pre_igloo_gap = IGLOO_GAP_BEFORE
                    for g in (self.spawner.obstacles, self.spawner.collectibles, self.spawner.special_items):
                        for s in list(g):
                            s.kill()
            elif self.pre_igloo_gap > 0.0:
                self.pre_igloo_gap -= dt
                if self.pre_igloo_gap <= 0.0:
                    # gap finished → spawn 3 igloos (one per lane) each with its own game
                    game_order = list(self.mini_kinds)
                    random.shuffle(game_order)
                    for lane_idx, Mini in enumerate(game_order):
                        ig = IglooItem(
                            lane_idx,
                            self.adjusted_lane_x,
                            PRESENT_SPEED * (1.0 + 0.3 * portion)
                        )
                        ig.game_cls = Mini
                        self.igloos.add(ig)
                        self.all_sprites.add(ig)

                    self.next_igloo_t = self._next_igloo_delay(current_speed)
                    self.pre_igloo_gap = 0.0

        # post-carrot spawn gap timer
        if self.post_carrot_gap > 0.0:
            self.post_carrot_gap = max(0.0, self.post_carrot_gap - dt)

        # spawn/update: no spawns during igloo calm zone, while igloos are present,
        # or during post-carrot 1s gap
        if self.pre_igloo_gap <= 0.0 and len(self.igloos) == 0 and self.post_carrot_gap <= 0.0:
            self.spawner.update(dt, current_speed)

        # sprites
        for spr in list(self.all_sprites):
            if isinstance(spr, FallingSprite):
                spr.update(dt, current_speed)
            else:
                spr.update(dt)
        for fx in list(self.fx_sprites):
            fx.update(dt)

        # player updated separately (so we can hide him visually)
        self.player.update(dt)

        # collisions (skip when phased)
        if self.state["phase_timer"] <= 0.0:
            self.spawner.handle_collisions(self.player, self.state)

            # presents
            picked = self.state.get("frame_collected_presents", 0)
            if picked > 0:
                self.shared["presents"] += picked
                self.state["pickup_flash"] = max(self.state["pickup_flash"], 0.12)
                if self.sounds.get("present"):
                    self.sounds["present"].play()

            # specials
            specials = [n.lower() for n in self.state.get("frame_collected_specials", [])]
            if specials:
                if any(("carrot" in n) for n in specials):
                    self.state["phase_kind"] = "carrot"
                    self.state["phase_timer"] = 2.0
                    self.state["phase_start_flash"] = 0.25
                    self.player_hidden = True   # hide main character
                    self._spawn_split_parts()
                if any(("moose" in n) for n in specials):
                    self.state["phase_kind"] = "moose"
                    self.state["phase_timer"] = 2.0
                    self.state["phase_start_flash"] = 0.25
                    self.player.set_mode("moose")
                if self.sounds.get("special"):
                    self.sounds["special"].play()

            # obstacle hits
            collide_fn = pygame.sprite.collide_circle_ratio(1.05)
            for ob in list(self.spawner.obstacles):
                if collide_fn(self.player, ob):
                    self.shared["hearts"] = max(0, self.shared["hearts"] - 1)
                    self.state["slow_timer"]  = max(self.state["slow_timer"], 1.0)
                    self.state["hit_flash"]   = max(self.state["hit_flash"], 0.25)
                    ob.kill()
                    if self.sounds.get("hit"):
                        self.sounds["hit"].play()

            # igloo pickup → open that igloo's specific minigame
            touched_igloo = pygame.sprite.spritecollide(
                self.player, self.igloos, dokill=True,
                collided=pygame.sprite.collide_circle_ratio(1.15)
            )
            if touched_igloo:
                ig = touched_igloo[0]
                Mini = getattr(ig, "game_cls", random.choice(self.mini_kinds))
                self.mini = Mini()
                self.in_minigame = True

        if self.shared["hearts"] <= 0:
            self.game_over = True
        self._current_speed_dbg = current_speed

    def draw(self, screen: pygame.Surface):
        self._draw_bg(screen)
        self.all_sprites.draw(screen)
        self.fx_sprites.draw(screen)

        # draw main player only if not hidden by carrot effect
        if not self.player_hidden:
            screen.blit(self.player.image, self.player.rect)

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
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov.fill((0,0,0,150))
            screen.blit(ov, (0,0))
            t = self.bigfont.render("GAME OVER", True, (255, 220, 220))
            screen.blit(t, t.get_rect(center=(WIDTH//2, HEIGHT//2)))

        # Minigame overlay on top
        if self.in_minigame and self.mini:
            self.mini.draw(screen, self.font, self.bigfont)

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
        return None

    def _load_split_images(self, size: int):
        imgs = []
        head_img = self._load_first_ok(HEAD_PATHS_TRY, size)
        if head_img:
            imgs.append(head_img)
        else:
            print("[Split] Head image not found; split effect disabled.")
            return []

        try:
            upper_img = pygame.image.load(str(UPPER_PATH)).convert_alpha()
            upper_img = pygame.transform.smoothscale(upper_img, (size, size))
        except Exception:
            upper_img = None
            print("[Split] Upper body image not found.")
        try:
            lower_img = pygame.image.load(str(LOWER_PATH)).convert_alpha()
            lower_img = pygame.transform.smoothscale(lower_img, (size, size))
        except Exception:
            lower_img = None
            print("[Split] Lower body image not found.")

        if upper_img:
            imgs.append(upper_img)
        if lower_img:
            imgs.append(lower_img)
        return imgs

    def _draw_bg(self, surf: pygame.Surface):
        img = self.bg_img
        h = img.get_height()
        y = -int(self.bg_offset % h)
        surf.blit(img, (0, y))
        surf.blit(img, (0, y + h))
        if y + h < HEIGHT:
            surf.blit(img, (0, y + h * 2))

    def _spawn_split_parts(self):
        if not self.split_images:
            return
        # clear previous parts if any
        if self.carrot_parts:
            for h in self.carrot_parts:
                h.kill()
            self.carrot_parts.clear()

        # one part per lane: Head, Upper, Lower (or however many we loaded)
        y = PLAYER_Y - 110
        self.carrot_parts = []
        for lane_idx, img in enumerate(self.split_images):
            if lane_idx >= len(self.lane_centers):
                break
            cx = int(self.lane_centers[lane_idx])
            spr = _SplitPart(self, img, (cx, y))
            self.fx_sprites.add(spr)
            self.carrot_parts.append(spr)

    def _next_igloo_delay(self, cur_speed: float) -> float:
        portion = min(
            1.0,
            max(
                0.0,
                (cur_speed - BG_SCROLL_SPEED_BASE) /
                max(1.0, (BG_SCROLL_SPEED_MAX - BG_SCROLL_SPEED_BASE))
            )
        )
        lo, hi = IGLOO_INTERVAL_RANGE
        k = 1.0 - 0.35 * portion
        return random.uniform(lo * k, hi * k)


class _SplitPart(pygame.sprite.Sprite):
    def __init__(self, scene: SnowyScene, img: pygame.Surface, center: tuple[int, int]):
        super().__init__()
        self.scene = scene
        self.base_image = img
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=center)
        self.t = 0.0
        self.base_center = center
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

        self.image = self.base_image.copy()
        self.image.fill((255,255,255,alpha), special_flags=pygame.BLEND_RGBA_MULT)


class _Player(pygame.sprite.Sprite):
    def __init__(self, adjusted_lane_x, start_lane=1):
        super().__init__()
        self.normal_image = self._load_or_make_normal()
        self.image = self.normal_image.copy()
        self.rect = self.image.get_rect(center=(adjusted_lane_x(start_lane), PLAYER_Y))

        self.lane = start_lane
        self.target_x = float(self.rect.centerx)
        self.speed_tween = PLAYER_TWEEN
        self._adjusted_lane_x = adjusted_lane_x
        self.radius = int(self.image.get_width() * 0.45)

        self.mode = "normal"
        self.moose_frames_run = []
        self.moose_frame_left = None
        self.moose_frame_right = None
        self.anim_idx = 0
        self.anim_timer = 0.0
        self.turn_timer = 0.0
        self.turn_dir = None

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

    def update(self, dt):
        dx = self.target_x - self.rect.centerx
        step = dx * min(1.0, self.speed_tween * dt)
        self.rect.centerx += step
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
            size = 64
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(surf, (245,245,255), (size//2, size//2), size//2)
            pygame.draw.circle(surf, (200,200,200), (size//2, size//2+6), size//2-6, 3)
            return surf
