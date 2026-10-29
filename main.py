import os, sys
import pygame 

SCREEN_W, SCREEN_H, FPS = 1000, 500, 60
RESTART_BUTTON = pygame.Rect(SCREEN_W // 2 - 110, 320, 220, 56) 
def asset(name): return os.path.join(os.path.dirname(os.path.abspath(__file__)), name) 
WHITE, BLACK = (255, 255, 255), (20, 20, 28) 

def draw_text(surf, text, font, color, pos, center=False):
    img = font.render(text, True, color) 
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos) 
    surf.blit(font.render(text, True, BLACK), rect.move(2, 2))
    surf.blit(img, rect) 

class Game:
    def __init__(self, screen):
        self.screen, self.state = screen, "title" 
        self.font, self.big_font = pygame.font.Font(None, 30), pygame.font.Font(None, 64)
        self.bg = pygame.transform.scale(pygame.image.load(asset("background.png")). convert(), (SCREEN_W, SCREEN_H)) 
    def draw(self):
        s = self.screen
        s.blit(self.bg, (0,0))
        if self.state == "title":
            shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA); shade.fill((0, 0, 0, 110)); s.blit(shade, (0, 0))
            draw_text(s, "MARIE'S Escape", self.big_font, WHITE, (SCREEN_W // 2, 170), center=True)
            pygame.draw.rect(s, (255, 128, 182), RESTART_BUTTON, border_radius=12); pygame.draw.rect(s, WHITE, RESTART_BUTTON, 3, border_radius=12)
            draw_text(s, "PLAY", self.font, WHITE, RESTART_BUTTON.center, center=True)
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.state == "title" and RESTART_BUTTON.collidepoint(event.pos):
            self.state = "playing"
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
 
def main():
    pygame.init(); pygame.display.set_caption("Marie's Escape ")
    clock, game = pygame.time.Clock(), Game(pygame.display.set_mode((SCREEN_W, SCREEN_H)))
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            game.handle_event(event)
        game.draw(); pygame.display.flip(); clock.tick(FPS)
 
if __name__ == "__main__":
    main()