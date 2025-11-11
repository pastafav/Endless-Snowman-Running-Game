"""
Hell map stage for Endless Snowman, using shared Spawner.

Run this file directly to try the hell stage, or call run_hell() from another module.
Assumes 'image/hell_background.png' exists.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pygame

from spawner import Spawner, FallingSprite, load_image, PresentItem, SpecialBuff, Obstacle

# --- Config ---
WIDTH, HEIGHT = 1280, 720
FPS = 60

HELL_BG_PATH = Path("image/hell_background2.jpg")  # expected to exist

# Lane geometry (same as snow map)
CENTER_LANES_PCT = 0.86
LANE_COUNT = 5
PLAYABLE_CENTER_LANES = 3
PLAYER_TWEEN = 14.0
PLAYER_Y = int(HEIGHT * 0.78)
HORIZONTAL_SPREAD = 0.7

# Speed model
BG_SCROLL_SPEED_BASE = 420
BG_SCROLL_SPEED_MAX = 1100
TIME_TO_MAX = 55.0
SPEED_CURVE = 0.8

# Assets (reuse existing ones for now; can be customized later)
OBSTACLE_PATHS = [Path("image/TreeOnFire_2.png"), Path("image/Lava_2.png"), Path("image/Fire_1.png")]
PRESENT_PATH = Path("image/Present_1.png")
SPECIAL_PATHS = [Path("image/Moose_item_1.png"), Path("image/Carrot_1.png"), Path("image/Icecube_1.png")]

PRESENT_SIZE = 80
OBSTACLE_SIZE = 100
SPECIAL_SIZE = 80
ASSET_SIZE_OVERRIDES = {
	 "IceShards_1": 200,
    "Moose_item_1": 170,
    "TreeOnFire_2": 200,
}

OBSTACLE_SPEED = 260
PRESENT_SPEED = 250
SPECIAL_SPEED = 240

OBSTACLE_INTERVAL_RANGE = (0.7, 1.2)
PRESENT_INTERVAL_RANGE  = (0.40, 0.80)
SPECIAL_INTERVAL_RANGE  = (7.0, 12.0)

SPAWN_ACCEL_FACTOR = 0.6

PRESENT_SCORE_VALUE = 1
SPECIAL_SCORE_BONUS = 5

OFFSCREEN_BUFFER = 40

RELATIVE_SCROLL_MODE = True
RELATIVE_EXTRA_SPEED_FACTOR = 1.0

# --- BG Music ---
pygame.mixer.music.load("sound/hellmode_bm.mp3") 
pygame.mixer.music.play(loops=-1)
pygame.mixer.music.set_volume(0.2)


def load_bg(path: Path) -> pygame.Surface:
	try:
		img = pygame.image.load(str(path)).convert_alpha()
	except Exception as e:
		# Fallback if image missing
		img = pygame.Surface((WIDTH, HEIGHT))
		img.fill((60, 20, 20))
		return img
	iw, ih = img.get_size()
	scale = WIDTH / iw
	new_w = WIDTH
	new_h = max(HEIGHT, int(ih * scale))
	return pygame.transform.smoothscale(img, (new_w, new_h))


# --- Lanes geometry ---
center_width = int(WIDTH * CENTER_LANES_PCT)
outer_width = (WIDTH - center_width) // 2
lane_centers = []
left_edge = outer_width
for i in range(PLAYABLE_CENTER_LANES):
	frac = (2 * i + 1) / (2 * PLAYABLE_CENTER_LANES)
	cx = left_edge + int(center_width * frac)
	lane_centers.append(cx)


def adjusted_lane_x(lane_index: int) -> int:
	if PLAYABLE_CENTER_LANES != 3:
		return lane_centers[lane_index]
	mid_x = lane_centers[1]
	if lane_index == 1:
		return mid_x
	edge_x = lane_centers[lane_index]
	return int(mid_x + (edge_x - mid_x) * HORIZONTAL_SPREAD)


class Player(pygame.sprite.Sprite):
	def __init__(self, start_lane=1):
		super().__init__()
		size = 64
		self.image = pygame.Surface((size, size), pygame.SRCALPHA)
		# Draw a red-tinted snowman for hell
		pygame.draw.circle(self.image, (255, 210, 210), (size//2, size//2), size//2)
		pygame.draw.circle(self.image, (180, 60, 60), (size//2, size//2+6), size//2-6, 3)
		self.rect = self.image.get_rect(center=(adjusted_lane_x(start_lane), PLAYER_Y))
		self.lane = start_lane
		self.target_x = float(self.rect.centerx)
		self.speed_tween = PLAYER_TWEEN

	def update(self, dt):
		dx = self.target_x - self.rect.centerx
		step = dx * min(1.0, self.speed_tween * dt)
		self.rect.centerx += step

	def move_left(self):
		self.lane = max(0, self.lane - 1)
		self.target_x = adjusted_lane_x(self.lane)

	def move_right(self):
		self.lane = min(PLAYABLE_CENTER_LANES - 1, self.lane + 1)
		self.target_x = adjusted_lane_x(self.lane)


def draw_scrolling_bg(surf: pygame.Surface, img: pygame.Surface, offset: float) -> None:
	h = img.get_height()
	y = -int(offset % h)
	surf.blit(img, (0, y))
	surf.blit(img, (0, y + h))
	if y + h < HEIGHT:
		surf.blit(img, (0, y + h*2))


def run_hell(reuse_display: bool = True) -> None:
	pygame.init()
	screen = pygame.display.get_surface() if reuse_display and pygame.display.get_surface() else pygame.display.set_mode((WIDTH, HEIGHT))
	pygame.display.set_caption("Hell Stage")
	clock = pygame.time.Clock()
	font = pygame.font.SysFont("Consolas", 20)

	bg_img = load_bg(HELL_BG_PATH)

	all_sprites = pygame.sprite.Group()
	player = Player(start_lane=1)
	all_sprites.add(player)

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

	state = {"score": 0, "active_buff": None}

	bg_offset = 0.0
	elapsed = 0.0
	running = True

	while running:
		dt = clock.tick(FPS) / 1000.0
		for ev in pygame.event.get():
			if ev.type == pygame.QUIT:
				running = False
			elif ev.type == pygame.KEYDOWN:
				if ev.key == pygame.K_ESCAPE:
					running = False
				elif ev.key in (pygame.K_LEFT, pygame.K_a):
					player.move_left()
				elif ev.key in (pygame.K_RIGHT, pygame.K_d):
					player.move_right()

		elapsed += dt
		portion = min(1.0, elapsed / max(0.001, TIME_TO_MAX))
		current_speed = BG_SCROLL_SPEED_BASE + (BG_SCROLL_SPEED_MAX - BG_SCROLL_SPEED_BASE) * (portion ** SPEED_CURVE)
		bg_offset -= current_speed * dt

		spawner.update(dt, current_speed)

		for spr in all_sprites:
			if isinstance(spr, FallingSprite):
				spr.update(dt, current_speed)
			else:
				spr.update(dt)

		spawner.handle_collisions(player, state)

		draw_scrolling_bg(screen, bg_img, bg_offset)
		all_sprites.draw(screen)

		hud1 = font.render(f"Hell • Score: {state['score']}", True, (240, 220, 220))
		hud2 = font.render(f"Speed: {int(current_speed)} px/s", True, (230, 200, 200))
		screen.blit(hud1, (10, 8))
		screen.blit(hud2, (10, 32))

		pygame.display.flip()

	# If this was launched standalone, quit fully; if reused, leave pygame running
	if not reuse_display:
		pygame.quit()
		sys.exit()


if __name__ == "__main__":
	run_hell(reuse_display=False)

