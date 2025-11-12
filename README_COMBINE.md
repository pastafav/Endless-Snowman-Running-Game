
# Combined Endless Snowman (Display from V2 + Effects from V1)

This combined project starts from **Endless-Snowman-Running-Game-map** (V2) for
map/display and spawning, and **integrates the gameplay effects** (pickups, power,
hit logic, minigame trigger patterns) from **P1-version1** (V1).

## What was done
1. **Base code**: copied V2 project into this folder.
2. **Effect logic reference**: imported V1 `player.py`, `effects.py`, `minigame.py`, and `run_player_demo.py`
   into `legacy_effects/` for implementation reference and reuse.
3. **Integration points (to apply in V2 main loops)**:
   - Use the spawner hooks already provided in V2 (`frame_collected_presents`, `frame_collected_specials`).
   - Add **power-mode / invincibility** and **blink flash** effects when collecting Carrot/Deer/Moose items.
   - Add **obstacle hit penalty** behavior in `Spawner.handle_collisions` consumer code (main loop),
     using V1's `HIT_DEADLY` equivalent logic (e.g., hearts or melt / restart).
   - Optional: import and adapt `legacy_effects.BlinkEffect` for a small flash on power pickup.
   - Optional: route a **House** / igloo-like special to a mini-game (see `legacy_effects/minigame.py`).
4. **No changes** were made to `spawner.py` file semantics; we extend handling in main loops.

## How to integrate (minimal code edits):

### A) Common helper: BlinkEffect
```python
# Put near the top of endless_runner_map.py and hell_stage.py
import pygame

class BlinkEffect:
    def __init__(self, target, duration=0.25):
        self.t = 0.0; self.dur = duration
    def trigger(self): self.t = self.dur
    def update(self, dt): self.t = max(0.0, self.t - dt) if self.t>0 else 0.0
    def draw(self, surf, size):
        if self.t<=0: return
        a = int(140 * (self.t / self.dur))
        overlay = pygame.Surface(size, pygame.SRCALPHA); overlay.fill((255,255,255,a))
        surf.blit(overlay, (0,0))
```

### B) In `endless_runner_map.py`:
- After creating `player`, add:
```python
blink = BlinkEffect(player)
game_power = {'mode':'normal','time':0.0,'hearts':3}
```
- After `spawner.handle_collisions(player, game_state)`, add:
```python
# Presents already increase score via spawner.
# Specials: power-up & blink; Icecube handled already for hell melt.
for name in game_state.get('frame_collected_specials', []):
    n = name.lower()
    if 'carrot' in n or 'moose' in n or 'deer' in n:
        game_power['mode'] = 'phase'
        game_power['time'] = 2.0
        blink.trigger()
```
- Obstacle hit (replace original passive code):
```python
if game_power['mode'] != 'phase':
    # Hurt on obstacle touch (simple hearts system)
    if pygame.sprite.spritecollide(player, spawner.obstacles, dokill=False):
        game_power['hearts'] = max(0, game_power['hearts'] - 1)
        blink.trigger()
        # brief grace
        game_power['mode'] = 'phase'; game_power['time'] = 1.0
        if game_power['hearts'] == 0:
            game_state['phase'] = 'melted'; paused = True
else:
    # Clear touched obstacles while invincible
    pygame.sprite.spritecollide(player, spawner.obstacles, dokill=True)
```
- Each frame end (logic update area):
```python
game_power['time'] = max(0.0, game_power['time'] - dt)
if game_power['time'] == 0.0 and game_power['mode'] != 'normal':
    game_power['mode'] = 'normal'
blink.update(dt)
```
- In draw/HUD area:
```python
# Hearts
hud_hearts = font.render(f"Hearts: {game_power['hearts']}", True, (240,80,80))
screen.blit(hud_hearts, (10, 128))

# Power overlay + blink
if game_power['mode'] == 'phase':
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((255,255,255,16))
    screen.blit(overlay, (0,0))
blink.draw(screen, (WIDTH, HEIGHT))
```

### C) In `hell_stage.py`:
Use the same integration (blink/power/hearts). Icecube continues to add melt time; obstacle hits reduce hearts or can drop melt immediately to 0 for game over—choose one scheme.

### D) Optional: Circle-collision for friendlier feel
```python
player.radius = max(player.rect.width, player.rect.height)//2
collider = pygame.sprite.collide_circle_ratio(1.15)
pygame.sprite.spritecollide(player, spawner.collectibles, dokill=True, collided=collider)
pygame.sprite.spritecollide(player, spawner.special_items, dokill=True, collided=collider)
```

## Files included here
- Base V2 project
- `legacy_effects/` with V1: `player.py`, `effects.py`, `minigame.py`, `run_player_demo.py` as reference

Follow the steps above to finalize the merge. You can also directly import utilities from `legacy_effects` if preferred.

Good luck!
