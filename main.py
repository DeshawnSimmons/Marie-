"""Marie: Escape the Levels - a run-and-jump platformer. Needs: pip install pygame
Keep background.png, tiles.png and the level*.txt files in the same folder.
Arrows/A-D move, Space/Up/W jump (press again in mid-air to double jump), Shift run, R restart, Esc quit."""
import math, os, random, sys
import pygame

TILE, SCREEN_W, SCREEN_H, FPS = 40, 1000, 500, 60  # world size comes from the level files: 250 x 25 tiles = 10,000 x 1,000 px
GRAVITY, MAX_FALL, WALK, RUN, ACCEL, FRICTION = 0.6, 14, 4.5, 7.0, 0.5, 0.80
JUMP_SPEED, JUMP_CUT, STOMP_BOUNCE, COYOTE, BUFFER = -12.5, -4, -9, 6, 6
TIME_LIMIT, DOUBLE_JUMP, AIR_JUMPS = 300, -11, 1
RESTART_BUTTON = pygame.Rect(SCREEN_W // 2 - 110, 320, 220, 56)
def asset(name): return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)

WHITE, BLACK = (255, 255, 255), (20, 20, 28)
COIN, COIN_DARK = (255, 214, 40), (210, 150, 20)
FOX, FOX_DARK, CREAM, SCARF = (236, 122, 42), (180, 80, 24), (255, 238, 214), (40, 110, 220)
BEETLE, BEETLE_DARK, POLE, PENNANT = (122, 66, 170), (80, 40, 120), (200, 200, 210), (60, 200, 110)


LEVELS = [f"level{n}.txt" for n in range(1, 100) if os.path.exists(asset(f"level{n}.txt"))]
SOLID = set("#BCU[]{}")

def draw_text(surf, text, font, color, pos, center=False):
    img = font.render(text, True, color)
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    surf.blit(font.render(text, True, BLACK), rect.move(2, 2))
    surf.blit(img, rect)

def star(cx, cy, outer, inner):
    return [(cx + math.cos(a) * r, cy + math.sin(a) * r) for k in range(10) for a, r in [(-math.pi / 2 + k * math.pi / 5, outer if k % 2 == 0 else inner)]]

def move_and_collide(body, level):
    """Moves body.x/y by its velocity, stops at solid tiles. Returns (hit_wall, on_ground, head_hits)."""
    hit_wall, on_ground, head_hits = False, False, []
    body.x += body.vx; body.rect.x = round(body.x)
    for _, _, t in level.solids_hitting(body.rect):
        if body.vx > 0: body.rect.right = t.left
        elif body.vx < 0: body.rect.left = t.right
        body.x, hit_wall = body.rect.x, True
    body.y += body.vy; body.rect.y = round(body.y)
    for c, r, t in level.solids_hitting(body.rect):
        if body.vy > 0: body.rect.bottom, on_ground = t.top, True
        elif body.vy < 0: body.rect.top = t.bottom; head_hits.append((c, r))
    if on_ground or head_hits: body.vy, body.y = 0, body.rect.y
    return hit_wall, on_ground, head_hits

class Level:
    def __init__(self, filename):
        rows = open(asset(filename)).read().splitlines()
        self.grid = [list(r.ljust(max(map(len, rows)))) for r in rows]
        self.cols, self.rows = len(self.grid[0]), len(self.grid)
        self.width_px, self.height_px = self.cols * TILE, self.rows * TILE
        self.coins, self.enemies, self.bumps, self.pipes = [], [], {}, {}  
        self.start, self.goal = (TILE * 2, TILE * 8), None
        for r, row in enumerate(self.grid):
            for c, ch in enumerate(row):
                x, y = c * TILE, r * TILE
                if ch == "o": self.coins.append(pygame.Rect(x + 10, y + 6, 20, 28))
                elif ch == "E": self.enemies.append(Enemy(x + 4, y + TILE - Enemy.H))
                elif ch == "P": self.start = (x + 6, y + TILE - Player.H)
                elif ch == "F": self.goal = pygame.Rect(x + 16, y - 9 * TILE, 8, 10 * TILE)
                elif ch.isdigit(): self.pipes.setdefault(ch, []).append((c, r + 1))
                if ch in "oEPF" or ch.isdigit(): self.grid[r][c] = " "
    def is_solid(self, c, r):
        if c < 0 or c >= self.cols: return True
        return 0 <= r < self.rows and self.grid[r][c] in SOLID
    def solids_hitting(self, rect):
        for r in range(rect.top // TILE, (rect.bottom - 1) // TILE + 1):
            for c in range(rect.left // TILE, (rect.right - 1) // TILE + 1):
                if self.is_solid(c, r): yield c, r, pygame.Rect(c * TILE, r * TILE, TILE, TILE)

class Enemy:
    W, H = 32, 30
    def __init__(self, x, y):
        self.rect, self.x, self.y = pygame.Rect(x, y, self.W, self.H), float(x), float(y)
        self.vx, self.vy, self.alive, self.squash, self.anim = -1.2, 0.0, True, 0, random.random() * 10
    def kill(self): self.alive, self.squash = False, 30
    def update(self, level):
        if not self.alive: self.squash -= 1; return
        self.anim += 0.15
        self.vy = min(self.vy + GRAVITY, MAX_FALL)
        hit_wall, on_ground, _ = move_and_collide(self, level)
        ahead = self.rect.right + 1 if self.vx > 0 else self.rect.left - 1
        if hit_wall or (on_ground and not level.is_solid(ahead // TILE, (self.rect.bottom + 1) // TILE)):
            self.vx = -self.vx  
    def draw(self, surf, cam):
        x, y = self.rect.x - cam[0], self.rect.y - cam[1]
        if not self.alive: pygame.draw.ellipse(surf, BEETLE, (x, y + self.H - 10, self.W, 10)); return
        step = math.sin(self.anim * 2) * 3
        for fx in (3 + step, 19 - step): pygame.draw.ellipse(surf, BLACK, (x + fx, y + 22, 10, 8))
        pygame.draw.ellipse(surf, BEETLE, (x, y, self.W, 28))
        pygame.draw.ellipse(surf, BEETLE_DARK, (x, y, self.W, 28), 2)
        look = -2 if self.vx < 0 else 2
        for ex in (x + 9, x + 23): pygame.draw.circle(surf, WHITE, (ex, y + 16), 5); pygame.draw.circle(surf, BLACK, (ex + look, y + 17), 2)
        for a, b in ((4, 13), (28, 19)): pygame.draw.line(surf, BLACK, (x + a, y + 9), (x + b, y + 12), 2)  

class Player:
    W, H = 28, 36
    def __init__(self, x, y):
        self.rect, self.x, self.y = pygame.Rect(x, y, self.W, self.H), float(x), float(y)
        self.vx = self.vy = self.anim = self.coyote = self.jump_buffer = self.combo = 0
        self.on_ground, self.dead, self.facing, self.prev_bottom = False, False, 1, self.rect.bottom
        self.air_jumps, self.puff = AIR_JUMPS, [0, 0, 0]  
    def update(self, keys, level, game):
        self.prev_bottom = self.rect.bottom
        left, right = keys[pygame.K_LEFT] or keys[pygame.K_a], keys[pygame.K_RIGHT] or keys[pygame.K_d]
        max_speed = RUN if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else WALK
        if left != right: self.facing = -1 if left else 1; self.vx += ACCEL * self.facing
        else: self.vx = 0 if abs(self.vx) < 0.1 else self.vx * FRICTION
        if abs(self.vx) > max_speed: self.vx = math.copysign(max(max_speed, abs(self.vx) - ACCEL), self.vx)
        self.coyote = COYOTE if self.on_ground else self.coyote - 1
        if self.on_ground: self.air_jumps = AIR_JUMPS
        if self.jump_buffer > 0 and self.coyote > 0:
            self.vy, self.jump_buffer, self.coyote = JUMP_SPEED - abs(self.vx) * 0.15, 0, 0
        elif self.jump_buffer == BUFFER and self.air_jumps > 0: 
            self.vy, self.jump_buffer, self.air_jumps = DOUBLE_JUMP, 0, self.air_jumps - 1
            self.puff = [self.rect.centerx, self.rect.bottom, 16]
        self.puff[2] = max(0, self.puff[2] - 1)
        self.jump_buffer = max(0, self.jump_buffer - 1)
        if not (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.vy < JUMP_CUT:
            self.vy = JUMP_CUT 
        self.vy = min(self.vy + GRAVITY, MAX_FALL)
        hit_wall, self.on_ground, head_hits = move_and_collide(self, level)
        if hit_wall: self.vx = 0
        if head_hits:
            c, r = min(head_hits, key=lambda h: abs(h[0] * TILE + TILE / 2 - self.rect.centerx))
            game.bump_block(c, r)
        if self.on_ground: self.combo, self.anim = 0, self.anim + abs(self.vx) * 0.08
    def draw(self, surf, cam):
        x, y, f = self.rect.x - cam[0], self.rect.y - cam[1], self.facing
        cx = x + self.W // 2
        grow = 16 - self.puff[2]  
        if self.puff[2]: pygame.draw.ellipse(surf, WHITE, (self.puff[0] - cam[0] - 10 - grow * 2, self.puff[1] - cam[1] - 4, 20 + grow * 4, 10), 3)
        pygame.draw.polygon(surf, FOX, [(cx - 8 * f, y + 22), (cx - 22 * f, y + 12), (cx - 20 * f, y + 28)])
        pygame.draw.circle(surf, CREAM, (int(cx - 20 * f), y + 14), 4)
        swing = 3 if not self.on_ground else (math.sin(self.anim) * 4 if abs(self.vx) > 0.2 else 0)
        for lx in (-8 + swing, 2 - swing): pygame.draw.rect(surf, FOX_DARK, (cx + lx, y + 28, 6, 8), border_radius=2)
        pygame.draw.ellipse(surf, FOX, (x + 3, y + 15, 22, 18))
        pygame.draw.ellipse(surf, CREAM, (cx - 5 + 2 * f, y + 19, 10, 12))
        pygame.draw.rect(surf, SCARF, (x + 5, y + 15, 18, 5), border_radius=2)
        pygame.draw.polygon(surf, SCARF, [(cx - 6 * f, y + 17), (cx - 13 * f, y + 24), (cx - 9 * f, y + 25)])
        hx, hy = cx + 3 * f, y + 9
        for s in (-1, 1): pygame.draw.polygon(surf, FOX_DARK, [(hx + 9 * s, hy - 3), (hx + 6 * s, hy - 14), (hx + s, hy - 6)])
        pygame.draw.circle(surf, FOX, (hx, hy), 9)
        pygame.draw.polygon(surf, CREAM, [(hx + 2 * f, hy), (hx + 13 * f, hy + 3), (hx + 2 * f, hy + 7)])
        pygame.draw.circle(surf, BLACK, (hx + 12 * f, hy + 3), 2)
        pygame.draw.circle(surf, BLACK, (hx + 4 * f, hy - 2), 2)

class Game:
    def __init__(self, screen):
        self.screen, self.state = screen, "title"
        self.font, self.big_font = pygame.font.Font(None, 30), pygame.font.Font(None, 64)
        self.bg = pygame.transform.scale(pygame.image.load(asset("background.png")).convert(), (SCREEN_W, SCREEN_H))
        sheet = pygame.image.load(asset("tiles.png")).convert_alpha() 
        self.tiles = [sheet.subsurface((i * TILE, 0, TILE, TILE)) for i in range(11)]
        self.edges = [self.tiles[5:7], [pygame.transform.flip(t, True, False) for t in self.tiles[5:7]]]
        self.reset(full=True)
    def reset(self, full=False):
        if full: self.score, self.coins, self.level_num = 0, 0, 0
        self.level = Level(LEVELS[self.level_num]); self.player = Player(*self.level.start)
        self.time_left, self.cam_x, self.cam_y, self.popups, self.timer, self.frame = TIME_LIMIT, 0, 0, [], 0, 0
    def add_coin(self): self.coins += 1
    def follow(self):  
        self.cam_x = max(0, min(self.player.rect.centerx - SCREEN_W * 0.4, self.level.width_px - SCREEN_W))
        self.cam_y = max(0, min(self.player.rect.centery - SCREEN_H * 0.55, self.level.height_px - SCREEN_H))
    def popup(self, text, x, y, coin=False):
        self.popups.append({"text": text, "x": x, "y": y, "t": 45, "coin": coin})
    def bump_block(self, c, r):
        self.level.bumps[(c, r)] = 10
        if self.level.grid[r][c] == "C":
            self.level.grid[r][c] = "U"; self.add_coin(); self.score += 200
            self.popup("+200", c * TILE + TILE // 2, r * TILE - 10, coin=True)
        for e in self.level.enemies:  
            if e.alive and e.rect.colliderect((c * TILE, r * TILE - 4, TILE, 4)):
                e.kill(); self.score += 100; self.popup("+100", e.rect.centerx, e.rect.top)
    def try_pipe(self): 
        p = self.player
        if not p.on_ground: return
        for caps in self.level.pipes.values():
            for c, r in caps:
                if len(caps) == 2 and p.rect.bottom == r * TILE and c * TILE + 4 <= p.rect.centerx <= c * TILE + 76:
                    self.pipe_from, self.pipe_to = (c, r), caps[1 - caps.index((c, r))]
                    self.state, self.timer, p.vx = "pipe", 70, 0
                    return
    def kill_player(self):
        self.player.dead, self.player.vy, self.player.vx, self.state, self.timer = True, -11, 0, "dying", 80
    def update(self, keys):
        self.frame += 1
        self.level.bumps = {k: t - 1 for k, t in self.level.bumps.items() if t > 1}
        for p in self.popups: p["t"], p["y"] = p["t"] - 1, p["y"] - 1.5
        self.popups = [p for p in self.popups if p["t"] > 0]
        if self.state == "playing": self.update_playing(keys)
        elif self.state == "pipe": 
            p, self.timer = self.player, self.timer - 1
            (c, r), t = (self.pipe_from if self.timer >= 35 else self.pipe_to), abs(self.timer - 35) / 35
            p.x, p.y = c * TILE + TILE - p.W // 2, r * TILE - p.H * t
            p.rect.topleft = (round(p.x), round(p.y))
            self.follow()
            if self.timer <= 0: self.state, p.vy = "playing", 0
        elif self.state == "dying":
            p = self.player
            p.vy = min(p.vy + GRAVITY, MAX_FALL); p.y += p.vy; p.rect.y = round(p.y); self.timer -= 1
            if self.timer <= 0: self.state = "gameover"
    def update_playing(self, keys):
        p, level = self.player, self.level
        p.update(keys, level, self)
        self.time_left = max(0, self.time_left - 1 / FPS)
        if self.time_left <= 0 or p.rect.top > level.height_px: return self.kill_player()
        self.follow()
        for coin in [c for c in level.coins if p.rect.colliderect(c)]:
            level.coins.remove(coin); self.add_coin(); self.score += 50
        for e in level.enemies:
            if e.rect.left < self.cam_x + SCREEN_W + 80: e.update(level)  
        level.enemies = [e for e in level.enemies if (e.alive or e.squash > 0) and e.rect.top < level.height_px]
        for e in level.enemies:
            if not e.alive or not p.rect.colliderect(e.rect): continue
            if p.vy > 0 and p.prev_bottom <= e.rect.top + 8:  
                e.kill(); p.combo += 1
                points = 100 * 2 ** min(p.combo - 1, 4)
                self.score += points; self.popup(f"+{points}", e.rect.centerx, e.rect.top)
                p.vy, p.rect.bottom, p.air_jumps = STOMP_BOUNCE, e.rect.top, AIR_JUMPS; p.y = p.rect.y
            else: return self.kill_player()
        if level.goal and p.rect.colliderect(level.goal):
            self.win_bonus = int(self.time_left) * 10
            self.score += self.win_bonus; self.state = "win"
    def draw_tile(self, ch, x, y, c, r):
        g = self.level.grid
        kind = {"#": 0 if r == 0 or g[r - 1][c] != "#" else 1, "B": 2, "C": 3, "U": 4, "[": 7, "]": 8, "{": 9, "}": 10}[ch]
        self.screen.blit(self.tiles[kind], (x, y))
        for side, nc in ((0, c - 1), (1, c + 1)):  
            if ch == "#" and 0 <= nc < self.level.cols and g[r][nc] != "#":
                self.screen.blit(self.edges[side][kind], (x, y))
    def draw(self):
        s, level, cam, cy = self.screen, self.level, int(self.cam_x), int(self.cam_y)
        off = int(cam * 0.3) % SCREEN_W  
        s.blit(self.bg, (-off, 0)); s.blit(self.bg, (SCREEN_W - off, 0))
        if self.state == "pipe": self.player.draw(s, (cam, cy))
        for r in range(cy // TILE, min(level.rows, (cy + SCREEN_H) // TILE + 2)):
            for c in range(max(0, cam // TILE), min(level.cols, (cam + SCREEN_W) // TILE + 2)):
                if level.grid[r][c] == " ": continue
                t = level.bumps.get((c, r))
                lift = int(math.sin((10 - t) / 10 * math.pi) * 8) if t else 0
                self.draw_tile(level.grid[r][c], c * TILE - cam, r * TILE - lift - cy, c, r)
        for coin in level.coins:
            w = max(4, int(20 * abs(math.cos(self.frame * 0.08 + coin.x * 0.01))))
            rect = pygame.Rect(0, 0, w, 26); rect.center = (coin.centerx - cam, coin.centery - cy)
            pygame.draw.ellipse(s, COIN, rect); pygame.draw.ellipse(s, COIN_DARK, rect, 2)
        if level.goal:
            g, wave = level.goal.move(-cam, -cy), math.sin(self.frame * 0.1) * 4
            pygame.draw.rect(s, POLE, g); pygame.draw.circle(s, COIN, (g.centerx, g.top), 8)
            pygame.draw.polygon(s, PENNANT, [(g.left, g.top + 12), (g.left - 50, g.top + 26 + wave), (g.left, g.top + 42)])
            pygame.draw.polygon(s, WHITE, star(g.left - 17, g.top + 27 + wave / 2, 7, 3))
        for e in level.enemies: e.draw(s, (cam, cy))
        if self.state != "pipe": self.player.draw(s, (cam, cy))
        for p in self.popups:
            if p["coin"]: pygame.draw.ellipse(s, COIN, (p["x"] - cam - 8, p["y"] - cy - 30, 16, 22))
            draw_text(s, p["text"], self.font, WHITE, (p["x"] - cam, p["y"] - cy), center=True)
        for text, color, x in ((f"SCORE {self.score:06d}", WHITE, 16), (f"COINS x{self.coins:02d}", COIN, 330),
                               (f"LV{self.level_num + 1}  TIME {int(self.time_left):03d}", WHITE, 790)):
            draw_text(s, text, self.font, color, (x, 12))
        overlays = {"title": ("Marie: Escape the Levels", []), "instructions": ("HOW TO PLAY", ["Arrows / A-D move, Space jump (twice to double jump), Shift run",
                                                         "Stomp beetles, bump star blocks, reach the flag!", "Press DOWN on a pink pipe to travel through it", "Click or press ENTER to start"]),
                    "gameover": ("GAME OVER", [f"Final score: {self.score}", "Click RESTART (or press ENTER)"]),
                    "win": (f"LEVEL {self.level_num + 1} CLEAR!", [f"Time bonus: {getattr(self, 'win_bonus', 0)}", f"Score: {self.score}",
                            "Press ENTER for the next level" if self.level_num + 1 < len(LEVELS) else "You beat the game! ENTER to play again"])}
        if self.state in overlays:
            shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA); shade.fill((0, 0, 0, 110)); s.blit(shade, (0, 0))
            title, lines = overlays[self.state]
            draw_text(s, title, self.big_font, WHITE, (SCREEN_W // 2, 170), center=True)
            for i, line in enumerate(lines): draw_text(s, line, self.font, WHITE, (SCREEN_W // 2, 240 + i * 34), center=True)
        if self.state in ("title", "gameover"):
            pygame.draw.rect(s, (255, 128, 182), RESTART_BUTTON, border_radius=12); pygame.draw.rect(s, WHITE, RESTART_BUTTON, 3, border_radius=12)
            draw_text(s, "PLAY" if self.state == "title" else "RESTART", self.font, WHITE, RESTART_BUTTON.center, center=True)
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and (self.state == "instructions" or self.state in ("title", "gameover") and RESTART_BUTTON.collidepoint(event.pos)):
            self.reset(full=True); self.state = "instructions" if self.state == "title" else "playing"  # menu -> instructions -> game
        if event.type != pygame.KEYDOWN: return
        if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.state in ("title", "instructions", "gameover", "win"):
            if self.state == "win" and self.level_num + 1 < len(LEVELS): self.level_num += 1; self.reset()
            elif self.state != "title": self.reset(full=True)
            self.state = "instructions" if self.state == "title" else "playing"
        elif event.key == pygame.K_r and self.state not in ("title", "instructions"): self.reset(full=True); self.state = "playing"
        elif event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w) and self.state == "playing":
            self.player.jump_buffer = BUFFER
        elif event.key in (pygame.K_DOWN, pygame.K_s) and self.state == "playing": self.try_pipe()

def main():
    pygame.init(); pygame.display.set_caption("Marie: Escape the Levels")
    clock, game = pygame.time.Clock(), Game(pygame.display.set_mode((SCREEN_W, SCREEN_H)))
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            game.handle_event(event)
        game.update(pygame.key.get_pressed()); game.draw(); pygame.display.flip(); clock.tick(FPS)

if __name__ == "__main__":
    main()