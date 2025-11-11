# endless_runner_map.py
# Requirements: pygame (pip install pygame)
# Put your chosen background image path into BG_PATH (current default uses the file you provided).

import pygame, sys, math
from pathlib import Path
from spawner import Spawner, FallingSprite, load_image, PresentItem, SpecialBuff, Obstacle

# --- Config ---
WIDTH, HEIGHT = 1280, 720            # window size (you can make it fullscreen or desktop size)
FPS = 60

# Put your image path here. If you keep the image at the given container path, use the same path.
BG_PATH = Path("image/background2.png")

# Appearance & lane sizing
CENTER_LANES_PCT = 0.86   # how much width the three center lanes occupy (85-90% you requested)
OUTER_LANE_PCT = (1.0 - CENTER_LANES_PCT) / 2.0  # each outer lane pct
LANE_COUNT = 5            # total lane blocks on the width
PLAYABLE_CENTER_LANES = 3 # middle lanes that player can use

PLAYER_TWEEN = 14.0       # smoothing for lane movement
PLAYER_Y = int(HEIGHT * 0.78)

# Background scrolling speed (vertical)
BG_SCROLL_SPEED_BASE = 400     # starting pixels per second (increased for a faster start)
BG_SCROLL_SPEED_MAX = 1000      # cap speed to avoid absurd values
# Old model used BG_ACCEL_PER_SEC; that required (MAX-BASE)/ACCEL seconds to hit max (≈27.5s for 800).
# New model: reach max within TIME_TO_MAX seconds regardless of values.
TIME_TO_MAX = 60.0             # slower ramp to max speed (increase if still too fast)
SPEED_CURVE = 0.6             # faster early growth than linear (<1 speeds up early ramp)

# --- Pygame init ---
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Snow Survivor - Map (Top-down)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Consolas", 20)

# --- Load & prepare background image ---
def load_bg(path):
    try:
        img = pygame.image.load(str(path)).convert_alpha()
    except Exception as e:
        print("Failed to load background image:", e)
        return None
    # scale to window width while preserving aspect ratio; we want full width
    iw, ih = img.get_size()
    scale = WIDTH / iw
    new_w = WIDTH
    new_h = max(HEIGHT, int(ih * scale))  # ensure at least screen tall
    img = pygame.transform.smoothscale(img, (new_w, new_h))
    return img

bg_img = load_bg(BG_PATH)
if bg_img is None:
    # fallback to blank background
    bg_img = pygame.Surface((WIDTH, HEIGHT))
    bg_img.fill((220, 235, 245))

# Try to load hell map background (fallbacks to normal bg if missing)
def try_load_first(paths):
    for p in paths:
        img = load_bg(p)
        if img is not None:
            return img
    return None

HELL_BG_CANDIDATES = [
    Path("image/hell_background.png"),
    Path("image/hell_background.jpg"),
    Path("image/hell_background.jpeg"),
]

# Prefer explicit updated hell background if present (user change), else fall back to candidates
HELL_BG_PATH = Path("image/hell_background2.jpg")
hell_bg_img = load_bg(HELL_BG_PATH) or try_load_first(HELL_BG_CANDIDATES) or bg_img

# Use a current background handle so we can switch maps
current_bg_img = bg_img

# --- Lanes geometry ---
center_width = int(WIDTH * CENTER_LANES_PCT)
outer_width = (WIDTH - center_width) // 2
# playable lanes x centers (three centers equally spaced inside center_width)
lane_centers = []
left_edge = outer_width
for i in range(PLAYABLE_CENTER_LANES):
    # position each center at 1/6, 3/6, 5/6 within the center_width
    frac = (2 * i + 1) / (2 * PLAYABLE_CENTER_LANES)  # 1/6, 3/6, 5/6 for 3 lanes
    cx = left_edge + int(center_width * frac)
    lane_centers.append(cx)

# Provide convenience mapping for 3 logical lanes: 0-left,1-mid,2-right
# (player will use these indices)
# Outer lanes exist visually left of outer_width and right of outer_width+center_width

# If you want to restrict how far left/right the player can actually travel relative to
# the visual lane centers, introduce a HORIZONTAL_SPREAD factor (0 < spread <= 1).
# spread = 1.0 means full lane center positions (original behavior).
# spread < 1.0 pulls the extreme lanes toward the middle, reducing horizontal travel.
HORIZONTAL_SPREAD = 0.7  # adjust this (e.g., 0.5 .. 0.85) to taste

# --- PCG / Spawning Config ---
from random import uniform, randint, choice
OBSTACLE_PATHS = [Path("image/Tree_1.png"), Path("image/IceShards_1.png")]  # frequent obstacles
PRESENT_PATH = Path("image/Present_1.png")  # very frequent collectible
SPECIAL_PATHS = [Path("image/Moose_item_1.png"), Path("image/Carrot_1.png")]  # rare buff items

# Hell-phase specific asset sets (used after entering an igloo)
HELL_OBSTACLE_PATHS = [Path("image/TreeOnFire_2.png"), Path("image/Lava_2.png"), Path("image/Fire_1.png")]
HELL_PRESENT_PATH = Path("image/Present_1.png")  # duplicate explicit path (avoid forward reference issues)
HELL_SPECIAL_PATHS = [Path("image/Moose_item_1.png"), Path("image/Carrot_1.png"), Path("image/Icecube_1.png")]  # reuse specials
HELL_ASSET_SIZE_OVERRIDES = {
    "IceShards_1": 120,
    "Moose_item_1": 130,
}

# Transition items
IGLOO_PATH = Path("image/Igloo_2.png")
IGLOO_SIZE = 140
IGLOO_TRIGGER_TIME = 70.0   # seconds survived before igloos appear in all lanes

# Hell-phase tuning
HELL_SPECIAL_INTERVAL_RANGE = (2.0, 4.0)  # make specials (icecubes) appear frequently in hell
HELL_INITIAL_MELT = 25.0  # seconds of survival when entering hell
ICECUBE_MELT_ADD = 12.0   # seconds added per icecube

PRESENT_SIZE = 56
OBSTACLE_SIZE = 75   # base size for generic obstacles (Tree)
SPECIAL_SIZE = 80     # base size for specials (Carrot)

# Asset-specific overrides (stem -> size) for fine control
ASSET_SIZE_OVERRIDES = {
    "IceShards_1": 120,      # significantly larger for visibility
    "Moose_item_1": 130,     # larger moose item
}

OBSTACLE_SPEED = 260
PRESENT_SPEED = 250
SPECIAL_SPEED = 240

OBSTACLE_INTERVAL_RANGE = (0.8, 1.4)
PRESENT_INTERVAL_RANGE  = (0.45, 0.85)
SPECIAL_INTERVAL_RANGE  = (8.0, 14.0)

SPAWN_ACCEL_FACTOR = 0.55  # interval reduction fraction when at max speed

PRESENT_SCORE_VALUE = 1
SPECIAL_SCORE_BONUS = 5  # placeholder extra score

OFFSCREEN_BUFFER = 40

def adjusted_lane_x(lane_index: int) -> int:
    """Return an adjusted x-position for a logical lane index applying HORIZONTAL_SPREAD.

    For 3 lanes, original centers are [L, M, R]. We blend outer lanes toward the middle:
        new_left  = mid + (L - mid) * spread
        new_right = mid + (R - mid) * spread
        middle stays the same.
    """
    if PLAYABLE_CENTER_LANES != 3:
        # Generic fallback: just return original lane center if not 3-lane layout.
        return lane_centers[lane_index]
    mid_x = lane_centers[1]
    if lane_index == 1:
        return mid_x
    edge_x = lane_centers[lane_index]
    return int(mid_x + (edge_x - mid_x) * HORIZONTAL_SPREAD)

# --- Player sprite (simple placeholder) ---
class Player(pygame.sprite.Sprite):
    def __init__(self, start_lane=1):
        super().__init__()
        # simple snowman placeholder: circle or you can replace with sprite image
        size = 64
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        # draw a pixel-art like snowman (simple)
        pygame.draw.circle(self.image, (245, 245, 255), (size//2, size//2), size//2)
        pygame.draw.circle(self.image, (200, 200, 200), (size//2, size//2+6), size//2-6, 3)
        # Start at adjusted lane x (so the restricted range is consistent from the outset)
        self.rect = self.image.get_rect(center=(adjusted_lane_x(start_lane), PLAYER_Y))
        self.lane = start_lane
        self.target_x = float(self.rect.centerx)
        self.speed_tween = PLAYER_TWEEN

    def update(self, dt):
        # Smoothly tween to target_x
        dx = self.target_x - self.rect.centerx
        step = dx * min(1.0, self.speed_tween * dt)
        self.rect.centerx += step

    def move_left(self):
        """Move one lane left, clamped, using adjusted lane positions."""
        self.lane = max(0, self.lane - 1)
        self.target_x = adjusted_lane_x(self.lane)

    def move_right(self):
        """Move one lane right, clamped, using adjusted lane positions."""
        self.lane = min(PLAYABLE_CENTER_LANES - 1, self.lane + 1)
        self.target_x = adjusted_lane_x(self.lane)

# --- Sprites groups ---
all_sprites = pygame.sprite.Group()
player = Player(start_lane=1)
all_sprites.add(player)

igloos = pygame.sprite.Group()          # transition targets

# Initialize shared spawner for obstacles/presents/specials
RELATIVE_SCROLL_MODE = True  # True: items move with background + their own extra speed
RELATIVE_EXTRA_SPEED_FACTOR = 1.0  # scale factor for their own speed component

spawner = Spawner(
    lane_centers=lane_centers,
    adjusted_lane_x=adjusted_lane_x,
    all_sprites=all_sprites,
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
    present_score_value=PRESENT_SCORE_VALUE,
    special_score_bonus=SPECIAL_SCORE_BONUS,
)

class Igloo(FallingSprite):
    def __init__(self, image, lane_index, extra_speed, adjusted_lane_x, offscreen_buffer=40, relative_scroll_mode=True, relative_extra_factor=1.0, top_offset: int = 8):
        # Create as a FallingSprite that starts at the top area and scrolls downward
        # with the world so the player can reach it naturally.
        super().__init__(
            image,
            lane_index,
            extra_speed,
            adjusted_lane_x,
            offscreen_buffer=offscreen_buffer,
            relative_scroll_mode=relative_scroll_mode,
            relative_extra_factor=relative_extra_factor,
        )
        # Start near top; keep some offset so HUD doesn't overlap.
        self.rect.top = top_offset
        self.rect.centerx = adjusted_lane_x(lane_index)
        # Igloo should scroll (not anchored) so player can collide.
        self._anchored = False

    def on_enter(self, state):
        state['phase'] = 'entered_igloo'

    def update(self, dt, current_speed=None):
        # Use normal FallingSprite movement so it drifts downward with background plus any extra speed.
        super().update(dt, current_speed)

game_state = {
    'score': 0,
    'active_buff': None,
    'phase': 'run',            # run | igloo_phase | entered_igloo | hell
}

hell_initialized = False  # spawner swap guard

def spawn_igloos(current_speed):
    # Clear other moving junk so focus is on igloos
    for g in (spawner.obstacles, spawner.collectibles, spawner.special_items):
        for spr in list(g):
            spr.kill()
    # Spawn one igloo per lane
    # compute a size that fits the center playable lane width (with small padding)
    lane_width = max(64, int(center_width / max(1, PLAYABLE_CENTER_LANES)))
    igloo_size = max(48, lane_width - 16)
    for lane in range(PLAYABLE_CENTER_LANES):
        img = load_image(IGLOO_PATH, igloo_size)
        # Anchor igloo at the top of the screen so it looks like the map end
        ig = Igloo(
            img,
            lane,
            current_speed * 0.35 + 140,  # give igloos their own downward speed so they are reachable soon
            adjusted_lane_x=adjusted_lane_x,
            offscreen_buffer=OFFSCREEN_BUFFER,
            relative_scroll_mode=True,      # move with background + extra speed
            relative_extra_factor=1.0,
            top_offset=8,
        )
        igloos.add(ig)
        all_sprites.add(ig)


# --- Background scroll state ---
bg_offset = 0.0
elapsed_run_time = 0.0  # seconds since leaving start screen (unpaused)
igloo_spawned = False
EXTRA_SPEED_FOR_IGLOO = 60.0  # slight drift in addition to background to approach player

# --- Main loop state ---
running = True
paused = False
show_start = True

# --- Helper: draw tiled vertical background ---
def draw_scrolling_bg(surf, img, offset):
    # offset in pixels (vertical). keep in [0, img_h)
    h = img.get_height()
    y = -int(offset % h)
    # draw two copies (cover entire screen)
    surf.blit(img, (0, y))
    surf.blit(img, (0, y + h))
    # if needed draw third copy for very large steps
    if y + h < HEIGHT:
        surf.blit(img, (0, y + h*2))

# --- Main loop ---
while running:
    dt = clock.tick(FPS) / 1000.0

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                running = False
            if game_state.get('phase') == 'melted' and ev.key == pygame.K_r:
                # Restart back at snow map initial state without quitting program
                game_state.clear()
                game_state.update({
                    'score': 0,
                    'active_buff': None,
                    'phase': 'run',
                })
                # Clear sprites except player
                for g in (spawner.obstacles, spawner.collectibles, spawner.special_items, igloos):
                    for spr in list(g):
                        spr.kill()
                # Reset timers/state
                elapsed_run_time = 0.0
                bg_offset = 0.0
                igloo_spawned = False
                paused = False
                current_bg_img = bg_img
                # Rebuild spawner to snow config
                spawner = Spawner(
                    lane_centers=lane_centers,
                    adjusted_lane_x=adjusted_lane_x,
                    all_sprites=all_sprites,
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
                    present_score_value=PRESENT_SCORE_VALUE,
                    special_score_bonus=SPECIAL_SCORE_BONUS,
                )
            if show_start:
                show_start = False
            elif ev.key == pygame.K_p:
                paused = not paused
            elif ev.key in (pygame.K_LEFT, pygame.K_a):
                if not paused:
                    player.move_left()
            elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                if not paused:
                    player.move_right()

    if not show_start and not paused:
        # scroll background
        # ------------ CHANGED DIRECTION HERE ------------
        # Subtracting makes the background scroll the opposite way.
        # If it previously looked like you were moving "backwards", this flips it.
        # Update elapsed run timer
        elapsed_run_time += dt

        # Compute current scroll speed with time-to-max scaling.
        # portion goes 0->1 over TIME_TO_MAX seconds, then clamps.
        portion = min(1.0, elapsed_run_time / max(0.001, TIME_TO_MAX))
        portion_curved = portion ** SPEED_CURVE
        current_speed = BG_SCROLL_SPEED_BASE + (BG_SCROLL_SPEED_MAX - BG_SCROLL_SPEED_BASE) * portion_curved

        bg_offset -= current_speed * dt
        # ------------------------------------------------

        # Trigger igloo phase after the threshold
        if (game_state['phase'] == 'run') and (elapsed_run_time >= IGLOO_TRIGGER_TIME) and not igloo_spawned:
            game_state['phase'] = 'igloo_phase'
            igloo_spawned = True
            spawn_igloos(current_speed)

        # Only spawn regular PCG entities during normal run phase
        if game_state['phase'] == 'run':
            spawner.update(dt, current_speed)

        # update sprites (pass current_speed so relative scroll mode works)
        for spr in all_sprites:
            if isinstance(spr, FallingSprite):
                spr.update(dt, current_speed)
            else:
                spr.update(dt)

        # Collisions
        spawner.handle_collisions(player, game_state)
        # Apply Icecube effect (hell survival) when collected
        if game_state.get('phase') == 'hell':
            for buff_name in game_state.get('frame_collected_specials', []):
                if buff_name.lower().startswith('icecube'):
                    game_state['melt'] = min(120.0, game_state.get('melt', 0.0) + ICECUBE_MELT_ADD)
        # Enter an igloo to transition
        for ig in pygame.sprite.spritecollide(player, igloos, dokill=True):
            if isinstance(ig, Igloo):
                ig.on_enter(game_state)
                # Switch to hell map background
                current_bg_img = hell_bg_img
                bg_offset = 0.0
                # Reset elapsed run timer so hell stage begins at base speed again
                elapsed_run_time = 0.0
                # initialize melt resource for hell survival
                game_state['melt'] = HELL_INITIAL_MELT
                game_state['phase'] = 'hell'
                # Rebuild spawner with hell asset configuration
                spawner = Spawner(
                    lane_centers=lane_centers,
                    adjusted_lane_x=adjusted_lane_x,
                    all_sprites=all_sprites,
                    obstacle_paths=HELL_OBSTACLE_PATHS,
                    present_path=HELL_PRESENT_PATH,
                    special_paths=HELL_SPECIAL_PATHS,
                    present_size=PRESENT_SIZE,
                    obstacle_size=OBSTACLE_SIZE,
                    special_size=SPECIAL_SIZE,
                    size_overrides=HELL_ASSET_SIZE_OVERRIDES,
                    obstacle_speed=OBSTACLE_SPEED,
                    present_speed=PRESENT_SPEED,
                    special_speed=SPECIAL_SPEED,
                    obstacle_interval=OBSTACLE_INTERVAL_RANGE,
                    present_interval=PRESENT_INTERVAL_RANGE,
                    special_interval=HELL_SPECIAL_INTERVAL_RANGE,
                    spawn_accel_factor=SPAWN_ACCEL_FACTOR,
                    base_speed=BG_SCROLL_SPEED_BASE,
                    max_speed=BG_SCROLL_SPEED_MAX,
                    offscreen_buffer=OFFSCREEN_BUFFER,
                    relative_scroll_mode=RELATIVE_SCROLL_MODE,
                    relative_extra_factor=RELATIVE_EXTRA_SPEED_FACTOR,
                    present_score_value=PRESENT_SCORE_VALUE,
                    special_score_bonus=SPECIAL_SCORE_BONUS,
                )
                hell_initialized = True
                # ensure any leftover igloos removed from all_sprites group (already killed by spritecollide)

        # Spawn during hell phase as well
        if game_state['phase'] == 'hell':
            spawner.update(dt, current_speed)
            # Hell-specific survival: decrease melt over time; when reaching 0 -> game over
            if 'melt' in game_state:
                # melt decreases over real time; collecting icecube will add to it (handled in SpecialBuff)
                game_state['melt'] = max(0.0, game_state['melt'] - dt)
                if game_state['melt'] <= 0.0:
                    # Do NOT close the game; just pause and show an overlay so player can restart.
                    game_state['melt'] = 0.0
                    game_state['phase'] = 'melted'
                    paused = True

    # --- Draw ---
    draw_scrolling_bg(screen, current_bg_img, bg_offset)

    # optional: draw subtle grid overlay to help check lane centers (remove in final)
    # grid color low alpha
    # for debug, we'll draw thin grid matching pixel-block look if you want
    # Uncomment if needed:
    # for x in range(0, WIDTH, 16):
    #     pygame.draw.line(screen, (255,255,255,20), (x,0), (x,HEIGHT))

    # draw lane separators (visual guides) - optional, comment out in final
    # compute three vertical guide lines at each playable lane center
    # draw faint lines
    for cx in lane_centers:
        pygame.draw.line(screen, (200, 230, 255, 60), (cx, 0), (cx, HEIGHT), 1)

    # sprites
    all_sprites.draw(screen)
    # spawner sprites already in all_sprites; optional category draw if desired:
    # spawner.obstacles.draw(screen)

    # HUD placeholders
    if show_start:
        # start overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 18, 28, 170))
        screen.blit(overlay, (0,0))
        title = pygame.font.SysFont("Consolas", 48).render("Snow Survivor - Press any key", True, (255,255,255))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 24))
    else:
        txt = font.render("Use Left/Right (A/D)  •  (P) Pause", True, (20, 30, 40))
        screen.blit(txt, (10, 8))
        hud_score = font.render(f"Score: {game_state['score']}", True, (28, 42, 58))
        screen.blit(hud_score, (10, 32))
        if game_state['active_buff']:
            hud_buff = font.render(f"Buff: {game_state['active_buff']}", True, (50, 70, 90))
            screen.blit(hud_buff, (10, 56))
        if game_state['phase'] == 'igloo_phase':
            hint = font.render("Choose an Igloo to enter — random mini game", True, (30, 45, 60))
            screen.blit(hint, (10, 104))
        if game_state.get('phase') in ('hell', 'melted') and 'melt' in game_state:
            melt_txt = font.render(f"Melt: {game_state['melt']:.1f}s", True, (200, 40, 40))
            screen.blit(melt_txt, (10, 104))
        if not paused:
            dbg_speed = font.render(f"Speed: {int(current_speed)} px/s", True, (30, 45, 60))
            screen.blit(dbg_speed, (10, 80))

    # Melt overlay and restart hint
    if game_state.get('phase') == 'melted':
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((20, 0, 0, 170))
        screen.blit(overlay, (0, 0))
        title = pygame.font.SysFont("Consolas", 42).render("The snowman melted!", True, (255, 220, 220))
        sub = pygame.font.SysFont("Consolas", 22).render("Press R to restart (snow map) or ESC to quit", True, (255, 230, 230))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 40))
        screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2 + 4))

    pygame.display.flip()

pygame.quit()
sys.exit()