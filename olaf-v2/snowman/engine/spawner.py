# snowman/engine/spawner.py
from __future__ import annotations
from pathlib import Path
from random import uniform, randint, choice
import pygame

# ---- asset cache -------------------------------------------------------------
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

# ---- sprite classes ----------------------------------------------------------
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
        # radius for robust circle collisions at high speed
        self.radius = max(self.rect.width, self.rect.height) // 2

    def update(self, dt: float, current_speed: float | None = None) -> None:
        if self._relative_scroll_mode and current_speed is not None:
            total_speed = current_speed + self.extra_speed * self._relative_extra_factor
        else:
            total_speed = self.extra_speed
        self.rect.y += total_speed * dt
        surf = pygame.display.get_surface()
        if surf and self.rect.top > surf.get_height() + self._offscreen_buffer:
            self.kill()

class Obstacle(FallingSprite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.radius = int(self.radius * 0.85)  # allow slight “graze”

    def on_player_hit(self, state: dict):
        # Scene will deduct hearts; we just mark feedback
        state["hit_flash"] = max(state.get("hit_flash", 0.0), 0.25)
        state["slow_timer"] = max(state.get("slow_timer", 0.0), 1.25)

class PresentItem(FallingSprite):
    def __init__(self, *args, score_value: int = 1, **kwargs):
        super().__init__(*args, **kwargs)
        self.radius = int(self.radius * 1.10)
        self._score_value = score_value

    def on_collect(self, state: dict):
        # Count handled in scene, but mark that we picked one this frame
        state["frame_collected_presents"] = state.get("frame_collected_presents", 0) + 1
        state["pickup_flash"] = max(state.get("pickup_flash", 0.0), 0.12)

class SpecialBuff(FallingSprite):
    def __init__(self, *args, buff_type: str, bonus: int = 5, **kwargs):
        super().__init__(*args, **kwargs)
        self.radius = int(self.radius * 1.15)
        self.buff_type = buff_type
        self._bonus = bonus

    def on_collect(self, state: dict):
        bt = self.buff_type.lower()
        # PHASE MODE (carrot / moose): fast + intangible + BG tint
        if "carrot" in bt:
            state["phase_kind"]  = "carrot"
            state["phase_timer"] = state.get("phase_timer", 0.0) + 2.8
            state["phase_start_flash"] = 0.30
            state["active_buff"] = "carrot"
        elif "moose" in bt:
            state["phase_kind"]  = "moose"
            state["phase_timer"] = state.get("phase_timer", 0.0) + 2.8
            state["phase_start_flash"] = 0.30
            state["active_buff"] = "moose"
        elif "ice" in bt:
            # optional count (scene will display)
            state["ice_collected"] = state.get("ice_collected", 0) + 1
            state["active_buff"] = "ice"

        fl = state.get("frame_collected_specials", [])
        fl.append(self.buff_type)
        state["frame_collected_specials"] = fl
        state["pickup_flash"] = max(state.get("pickup_flash", 0.0), 0.12)

# ---- spawner -----------------------------------------------------------------
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
        # speed scale
        base_speed: float = 140.0,
        max_speed: float = 800.0,
        # movement behavior
        offscreen_buffer: int = 40,
        relative_scroll_mode: bool = True,
        relative_extra_factor: float = 1.0,
        # scoring
        present_score_value: int = 1,
        special_score_bonus: int = 5,
        # spawn safety
        min_lane_gap_px: int = 220,
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
        self.min_lane_gap_px = min_lane_gap_px

        self.all_sprites = all_sprites
        self.obstacles = pygame.sprite.Group()
        self.collectibles = pygame.sprite.Group()
        self.special_items = pygame.sprite.Group()

        self.next_obstacle_time = self._rand_interval(self.obstacle_interval)
        self.next_present_time = self._rand_interval(self.present_interval)
        self.next_special_time = self._rand_interval(self.special_interval)

        # per-lane cooldowns to avoid overlapping spawns in the same lane
        self._lane_block_timers: list[float] = [0.0 for _ in self.lane_centers]

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
        available = [i for i, t in enumerate(self._lane_block_timers) if t <= 0.0]
        if not available:
            # No safe lane right now; try a bit later
            self.next_obstacle_time += 0.05
            return
        lane = choice(available)
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
        # set lane block time based on combined downward speed
        if self.relative_scroll_mode:
            total_speed = current_speed + (self.obstacle_speed * speed_scale * self.relative_extra_factor)
        else:
            total_speed = self.obstacle_speed * speed_scale
        gap_px = self.min_lane_gap_px + img.get_height() * 0.5
        cooldown = gap_px / max(1.0, total_speed)
        self._lane_block_timers[lane] = max(self._lane_block_timers[lane], cooldown)

    def _spawn_present(self, current_speed: float) -> None:
        available = [i for i, t in enumerate(self._lane_block_timers) if t <= 0.0]
        if not available:
            self.next_present_time += 0.05
            return
        lane = choice(available)
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
        if self.relative_scroll_mode:
            total_speed = current_speed + (self.present_speed * speed_scale * self.relative_extra_factor)
        else:
            total_speed = self.present_speed * speed_scale
        gap_px = self.min_lane_gap_px + img.get_height() * 0.5
        cooldown = gap_px / max(1.0, total_speed)
        self._lane_block_timers[lane] = max(self._lane_block_timers[lane], cooldown)

    def _spawn_special(self, current_speed: float) -> None:
        available = [i for i, t in enumerate(self._lane_block_timers) if t <= 0.0]
        if not available:
            self.next_special_time += 0.05
            return
        lane = choice(available)
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
        if self.relative_scroll_mode:
            total_speed = current_speed + (self.special_speed * speed_scale * self.relative_extra_factor)
        else:
            total_speed = self.special_speed * speed_scale
        gap_px = self.min_lane_gap_px + img.get_height() * 0.5
        cooldown = gap_px / max(1.0, total_speed)
        self._lane_block_timers[lane] = max(self._lane_block_timers[lane], cooldown)

    # API ----------------------------------------------------------------------
    def update(self, dt: float, current_speed: float) -> None:
        # decrement per-lane block timers
        for i in range(len(self._lane_block_timers)):
            if self._lane_block_timers[i] > 0.0:
                self._lane_block_timers[i] = max(0.0, self._lane_block_timers[i] - dt)

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
        """Circle collisions (robust at speed). Scene can decide immunity."""
        state["frame_collected_presents"] = 0
        state["frame_collected_specials"] = []

        for c in pygame.sprite.spritecollide(
            player, self.collectibles, dokill=True,
            collided=pygame.sprite.collide_circle_ratio(1.25)
        ):
            if isinstance(c, PresentItem):
                c.on_collect(state)

        for sp in pygame.sprite.spritecollide(
            player, self.special_items, dokill=True,
            collided=pygame.sprite.collide_circle_ratio(1.25)
        ):
            if isinstance(sp, SpecialBuff):
                sp.on_collect(state)

        for ob in pygame.sprite.spritecollide(
            player, self.obstacles, dokill=False,
            collided=pygame.sprite.collide_circle_ratio(1.05)
        ):
            if isinstance(ob, Obstacle):
                ob.on_player_hit(state)
