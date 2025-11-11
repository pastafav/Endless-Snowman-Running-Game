"""
Spawner module: shared sprite classes and procedural spawning for Endless Snowman.

Usage:
- Construct Spawner with lane_centers and an adjusted_lane_x callable
- Provide asset paths, sizes, speeds, intervals
- Call spawner.update(dt, current_speed) each frame during the normal run phase
- Use spawner.handle_collisions(player, game_state) to process pickups/hits
- Sprites are added to the provided all_sprites group for drawing
"""
from __future__ import annotations

from pathlib import Path
from random import uniform, randint, choice
import pygame

# Asset cache and loader -------------------------------------------------------
_asset_cache: dict[tuple[Path, int | None], pygame.Surface] = {}

def load_image(path: Path, size: int | None = None) -> pygame.Surface:
    key = (path, size)
    if key in _asset_cache:
        return _asset_cache[key]
    try:
        img = pygame.image.load(str(path)).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, (size, size))
    except Exception:
        img = pygame.Surface((size or 64, size or 64), pygame.SRCALPHA)
        img.fill((180, 60, 60, 230))
    _asset_cache[key] = img
    return img

# Sprite classes ---------------------------------------------------------------
class FallingSprite(pygame.sprite.Sprite):
    def __init__(
        self,
        image: pygame.Surface,
        lane_index: int,
        extra_speed: float,
        adjusted_lane_x,
        offscreen_buffer: int = 40,
        relative_scroll_mode: bool = True,
        relative_extra_factor: float = 1.0,
    ) -> None:
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.centerx = adjusted_lane_x(lane_index)
        self.rect.top = -self.rect.height
        self.extra_speed = extra_speed
        self._adjusted_lane_x = adjusted_lane_x
        self._offscreen_buffer = offscreen_buffer
        self._relative_scroll_mode = relative_scroll_mode
        self._relative_extra_factor = relative_extra_factor

    def update(self, dt: float, current_speed: float | None = None) -> None:
        if self._relative_scroll_mode and current_speed is not None:
            total_speed = current_speed + self.extra_speed * self._relative_extra_factor
        else:
            total_speed = self.extra_speed
        self.rect.y += total_speed * dt
        if self.rect.top > pygame.display.get_surface().get_height() + self._offscreen_buffer:
            self.kill()

class Obstacle(FallingSprite):
    def on_player_hit(self, state):
        # Placeholder: implement obstacle penalty later in player/effects system
        pass

class PresentItem(FallingSprite):
    def __init__(self, *args, score_value: int = 1, **kwargs):
        super().__init__(*args, **kwargs)
        self._score_value = score_value
    def on_collect(self, state):
        state['score'] = state.get('score', 0) + self._score_value

class SpecialBuff(FallingSprite):
    def __init__(self, *args, buff_type: str, bonus: int = 5, **kwargs):
        super().__init__(*args, **kwargs)
        self.buff_type = buff_type
        self._bonus = bonus
    def on_collect(self, state):
        # Default effect: add bonus score and mark active buff
        state['score'] = state.get('score', 0) + self._bonus
        state['active_buff'] = self.buff_type
        # Special-case: Icecube restores 'melt' (survival) in hell map
        try:
            if self.buff_type.lower().startswith('icecube'):
                # add melt seconds; if 'melt' isn't present, initialize it
                state['melt'] = state.get('melt', 0) + 12.0
        except Exception:
            # be defensive: don't allow a buff to crash the game
            pass

# Spawner ----------------------------------------------------------------------
class Spawner:
    def __init__(
        self,
        *,
        lane_centers: list[int],
        adjusted_lane_x,
        all_sprites: pygame.sprite.Group,
        # assets
        obstacle_paths: list[Path],
        present_path: Path,
        special_paths: list[Path],
        # sizes
        present_size: int,
        obstacle_size: int,
        special_size: int,
        size_overrides: dict[str, int] | None = None,
        # speeds
        obstacle_speed: float = 260,
        present_speed: float = 250,
        special_speed: float = 240,
        # spawn intervals (lo, hi)
        obstacle_interval: tuple[float, float] = (0.8, 1.4),
        present_interval: tuple[float, float] = (0.45, 0.85),
        special_interval: tuple[float, float] = (8.0, 14.0),
        spawn_accel_factor: float = 0.55,
        # speed range for normalization
        base_speed: float = 140.0,
        max_speed: float = 800.0,
        # movement behavior
        offscreen_buffer: int = 40,
        relative_scroll_mode: bool = True,
        relative_extra_factor: float = 1.0,
        # scoring
        present_score_value: int = 1,
        special_score_bonus: int = 5,
    ) -> None:
        self.lane_centers = lane_centers
        self.adjusted_lane_x = adjusted_lane_x
        self.obstacle_paths = obstacle_paths
        self.present_path = present_path
        self.special_paths = special_paths
        self.present_size = present_size
        self.obstacle_size = obstacle_size
        self.special_size = special_size
        self.size_overrides = size_overrides or {}
        self.obstacle_speed = obstacle_speed
        self.present_speed = present_speed
        self.special_speed = special_speed
        self.obstacle_interval = obstacle_interval
        self.present_interval = present_interval
        self.special_interval = special_interval
        self.spawn_accel_factor = spawn_accel_factor
        self.base_speed = base_speed
        self.max_speed = max_speed
        self.offscreen_buffer = offscreen_buffer
        self.relative_scroll_mode = relative_scroll_mode
        self.relative_extra_factor = relative_extra_factor
        self.present_score_value = present_score_value
        self.special_score_bonus = special_score_bonus

        # sprite groups
        self.all_sprites = all_sprites
        self.obstacles = pygame.sprite.Group()
        self.collectibles = pygame.sprite.Group()
        self.special_items = pygame.sprite.Group()

        # timers
        self.next_obstacle_time = self._rand_interval(self.obstacle_interval)
        self.next_present_time = self._rand_interval(self.present_interval)
        self.next_special_time = self._rand_interval(self.special_interval)

    # helpers ------------------------------------------------------------------
    def _size_for_path(self, path: Path, default_size: int) -> int:
        return self.size_overrides.get(path.stem, default_size)

    def _rand_interval(self, pair: tuple[float, float]) -> float:
        return uniform(*pair)

    def _speed_portion(self, current_speed: float) -> float:
        denom = max(1.0, (self.max_speed - self.base_speed))
        return min(1.0, (current_speed - self.base_speed) / denom)

    def _scaled_interval(self, base_range: tuple[float, float], current_speed: float) -> tuple[float, float]:
        portion = self._speed_portion(current_speed)
        reduction = self.spawn_accel_factor * portion
        lo, hi = base_range
        return (lo * (1 - reduction), hi * (1 - reduction))

    # spawning -----------------------------------------------------------------
    def _spawn_obstacle(self, current_speed: float) -> None:
        lane = randint(0, len(self.lane_centers) - 1)
        path = choice(self.obstacle_paths)
        size = self._size_for_path(path, self.obstacle_size)
        img = load_image(path, size)
        speed_scale = 1.0 + self._speed_portion(current_speed) * 0.35
        sprite = Obstacle(
            img, lane, self.obstacle_speed * speed_scale,
            adjusted_lane_x=self.adjusted_lane_x,
            offscreen_buffer=self.offscreen_buffer,
            relative_scroll_mode=self.relative_scroll_mode,
            relative_extra_factor=self.relative_extra_factor,
        )
        self.obstacles.add(sprite)
        self.all_sprites.add(sprite)

    def _spawn_present(self, current_speed: float) -> None:
        lane = randint(0, len(self.lane_centers) - 1)
        img = load_image(self.present_path, self.present_size)
        speed_scale = 1.0 + self._speed_portion(current_speed) * 0.6
        sprite = PresentItem(
            img, lane, self.present_speed * speed_scale,
            adjusted_lane_x=self.adjusted_lane_x,
            offscreen_buffer=self.offscreen_buffer,
            relative_scroll_mode=self.relative_scroll_mode,
            relative_extra_factor=self.relative_extra_factor,
            score_value=self.present_score_value,
        )
        self.collectibles.add(sprite)
        self.all_sprites.add(sprite)

    def _spawn_special(self, current_speed: float) -> None:
        lane = randint(0, len(self.lane_centers) - 1)
        path = choice(self.special_paths)
        size = self._size_for_path(path, self.special_size)
        img = load_image(path, size)
        speed_scale = 1.0 + self._speed_portion(current_speed) * 0.30
        sprite = SpecialBuff(
            img, lane, self.special_speed * speed_scale,
            adjusted_lane_x=self.adjusted_lane_x,
            offscreen_buffer=self.offscreen_buffer,
            relative_scroll_mode=self.relative_scroll_mode,
            relative_extra_factor=self.relative_extra_factor,
            buff_type=path.stem,
            bonus=self.special_score_bonus,
        )
        self.special_items.add(sprite)
        self.all_sprites.add(sprite)

    # API ----------------------------------------------------------------------
    def update(self, dt: float, current_speed: float) -> None:
        self.next_obstacle_time -= dt
        self.next_present_time -= dt
        self.next_special_time -= dt
        if self.next_obstacle_time <= 0:
            self._spawn_obstacle(current_speed)
            self.next_obstacle_time = self._rand_interval(self._scaled_interval(self.obstacle_interval, current_speed))
        if self.next_present_time <= 0:
            self._spawn_present(current_speed)
            self.next_present_time = self._rand_interval(self._scaled_interval(self.present_interval, current_speed))
        if self.next_special_time <= 0:
            self._spawn_special(current_speed)
            self.next_special_time = self._rand_interval(self._scaled_interval(self.special_interval, current_speed))

    def handle_collisions(self, player: pygame.sprite.Sprite, state: dict) -> None:
        # reset per-frame collection trackers
        state['frame_collected_presents'] = 0
        state['frame_collected_specials'] = []

        for c in pygame.sprite.spritecollide(player, self.collectibles, dokill=True):
            if isinstance(c, PresentItem):
                c.on_collect(state)
                state['frame_collected_presents'] += 1
        for sp in pygame.sprite.spritecollide(player, self.special_items, dokill=True):
            if isinstance(sp, SpecialBuff):
                sp.on_collect(state)
                try:
                    state['frame_collected_specials'].append(sp.buff_type)
                except Exception:
                    pass
        for ob in pygame.sprite.spritecollide(player, self.obstacles, dokill=False):
            if isinstance(ob, Obstacle):
                ob.on_player_hit(state)
