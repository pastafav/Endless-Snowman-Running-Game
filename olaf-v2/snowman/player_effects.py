import pygame

class BlinkEffect:
    """Quick white flash that fades (used on power pickup / damage)."""
    def __init__(self, duration: float = 0.25):
        self.t = 0.0
        self.dur = duration

    def trigger(self):
        self.t = self.dur

    def update(self, dt: float):
        if self.t > 0:
            self.t = max(0.0, self.t - dt)

    def draw(self, surf: pygame.Surface, size: tuple[int, int]):
        if self.t <= 0:
            return
        a = int(140 * (self.t / self.dur))
        overlay = pygame.Surface(size, pygame.SRCALPHA)
        overlay.fill((255, 255, 255, a))
        surf.blit(overlay, (0, 0))
