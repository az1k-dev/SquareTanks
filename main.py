import pygame
import math
import os
import sys
import random

pygame.init()

# Program settings
FPS = 60

SCREEN_SIZE = (1800, 900)
width = SCREEN_SIZE[0]
height = SCREEN_SIZE[1]

clock = pygame.time.Clock()

COLORS = ['green', 'red']

screen = pygame.display.set_mode(SCREEN_SIZE)

# Load sounds
BOOM_SOUND = pygame.mixer.Sound('data/boom_sound.wav')
SHOT_SOUND = pygame.mixer.Sound('data/shot_sound.wav')
MUSIC = pygame.mixer.Sound('data/music.wav')
RELOAD_SOUND = pygame.mixer.Sound('data/reload_sound.wav')


# Function for calculating sin(from degrees)
def sin(x):
    return math.sin(math.radians(x))


# Function for calculating cos(from degrees)
def cos(x):
    return math.cos(math.radians(x))


# Function for calculating hypotenuse(from a, b)
def hypotenuse(a, b):
    return math.sqrt(a ** 2 + b ** 2)


# Function for image loading
def load_image(name, colorkey=None):
    # Find path to image and load it
    fullname = os.path.join('data', name)
    image = pygame.image.load(fullname).convert()

    # Make image transparent
    if colorkey is not None:
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()

    return image


# Function for getting level's list
def get_level_list():
    return os.listdir('levels')


# Function for loading levels
def load_level(filename):
    # Create full path to level
    filename = "levels/" + filename

    # Open and read level file
    with open(filename, 'r') as level_file:
        level_map = [line.strip() for line in level_file]

    # Find max width of string
    max_width = max(map(len, level_map))

    # Return level with emptiness completion
    return list(map(lambda x: x.ljust(max_width, '0'), level_map))


# Class for border of game field
class Border(pygame.sprite.Sprite):
    def __init__(self, x1, y1, x2, y2, edge):
        super().__init__(borders)
        self.edge = edge
        if x1 == x2:
            self.rect = pygame.Rect(x1, y1, 1, y2 - y1)
            self.plane = 0
        else:
            self.rect = pygame.Rect(x1, y1, x2 - x1, 1)
            self.plane = 1


# Class of the tank sprite
class Tank(pygame.sprite.Sprite):
    def __init__(self, pos, color, number, *groups):
        super().__init__(groups)

        # Tank's options
        self.rotate_speed = 180
        self.speed = 200
        self.reload_time = 1
        self.bullet_speed = 500
        self.color = color
        self.number = number

        # Changeable tank's options
        self.gun_angle = 0
        self.body_angle = 90
        self.reload_frames = 0

        self.not_moved_in_frame = True
        self.destroyed = False
        self.new_round_countdown = FPS * 2
        self.orig_reload_frames = self.reload_time * FPS

        self.bullets = []

        # Load tank's images
        self.body_image = load_image(f'tank_body_{color}.png')
        self.gun_image = load_image(f'tank_barrel_{color}.png', 0)

        # Create tank's image and borders
        self.body = pygame.transform.rotate(self.body_image,
                                            (self.body_angle + 90) % 360)
        self.rect = self.body.get_rect()
        self.rect.x, self.rect.y = pos

        self.gun = self.gun_image.copy()
        self.gun_rect = self.gun.get_rect(center=self.rect.center)

    # Function for gun rotating
    def rotate_gun(self, right=True):
        # right option - direction of rotating
        # (True - clockwise, False - counterclockwise)
        if right:
            self.gun_angle = (self.gun_angle + self.rotate_speed / FPS) % 360
        else:
            self.gun_angle = (self.gun_angle - self.rotate_speed / FPS) % 360

    # Function for tank's move
    def move(self, direction):
        # direction option - direction of move(up, down, right, left)

        # Check if tank not moved in frame
        if self.not_moved_in_frame:
            # Словарь с параметрами для каждого из направлений движения
            direction_dict = {
                'up': {'plane': 1, 'direction': -1, 'angle': 270},
                'down': {'plane': 1, 'direction': 1, 'angle': 90},
                'right': {'plane': 0, 'direction': 1, 'angle': 180},
                'left': {'plane': 0, 'direction': -1, 'angle': 0},
            }

            # Get current direction parameters
            direction_params = direction_dict[direction]

            # Edit tank's coordinates and body angle
            self.rect[direction_params['plane']] += int(self.speed / FPS) * \
                                                    direction_params['direction']

            self.body_angle = direction_params['angle']

            # Edit parameter for exclude situation
            # of more than one move in frame
            self.not_moved_in_frame = False

            # Check if tank have collision
            collision_blocks = pygame.sprite.spritecollide(
                self, obstacles, False
            )

            collision_blocks.remove(self)

            # If there is collision, start cycle
            # for return tank to start coordinates
            while collision_blocks:
                # Start function for return tank to start coordinates
                self.control_collision(collision_blocks[0],
                                       direction_params['plane'])

                # Check tank's collision
                collision_blocks = pygame.sprite.spritecollide(
                    self, obstacles, False
                )

                collision_blocks.remove(self)

            # Check tank's collision with borders
            collision_border = pygame.sprite.spritecollide(self, borders, False)

            # If there is collision with borders,
            # return tank to start coordinates
            for collide in collision_border:
                self.rect[collide.plane] = \
                    (SCREEN_SIZE[collide.plane] - 50) * collide.edge

    # Function for returning tank to start coordinates without collision
    def control_collision(self, collide, i):
        if self.rect[i] < collide.rect[i]:
            self.rect[i] = collide.rect[i] - self.rect.size[i]
        else:
            self.rect[i] = collide.rect[i] + collide.rect.size[i]

    # Function for starting new round if tank is destroyed
    def check_destroy(self):
        # Check if tank is destroyed
        if self.destroyed:
            # If countdown not equal 0 decrease countdown
            if self.new_round_countdown != 0:
                self.new_round_countdown -= 1
            # If countdown equal 0 start new round
            elif self.new_round_countdown == 0:
                new_round()

    def action(self, command):
        # Function for pass commands to tank
        # command parameter - command for tank
        # command format - command/parameter

        # Check tank isn't destroyed
        if not self.destroyed:
            # Separate command to command and perameter
            command, parameter = command.split('/')

            # Command doing
            if command == 'move':
                self.move(parameter)
            elif command == 'rotate_gun':
                self.rotate_gun({'true': True, 'false': False}[parameter])
            elif command == 'fire':
                self.fire()

    def update(self):
        # Update tank in new frame
        if not self.destroyed:
            # Update parameter for checking if tank moved in current frame
            self.not_moved_in_frame = True

            # Edit tank's image by direction
            self.body = pygame.transform.rotate(
                self.body_image, (self.body_angle + 90) % 360
            )

            # Edit gun's image and gun's rectangle by direction
            self.gun = pygame.transform.rotate(self.gun_image, self.gun_angle)
            self.gun_rect = self.gun.get_rect(center=self.rect.center)

            # Reduce frame's count to gun reload
            if self.reload_frames > 0:
                self.reload_frames -= 1

            # Get all bullet's without own
            frame_bullets = bullets.copy()
            for i in self.bullets:
                frame_bullets.remove(i)

            # Check if tank collides with bullets
            bullets_collide = pygame.sprite.spritecollideany(self, frame_bullets)
            if bullets_collide:
                # If tank collides with bullets, start boom function
                bullets_collide.destroy()
                self.boom()

    def boom(self):
        # Tank destroying function

        # Boom sound playing
        BOOM_SOUND.set_volume(1)
        BOOM_SOUND.play()

        # Switch variable of tank's destroying
        self.destroyed = True

        # Start explosion animation
        Explosion(self.rect.center, 1)

        # Create empty function - stub
        def destroyed_draw(surface):
            pass

        # Drawing functions replace with empty function
        self.draw_body = destroyed_draw
        self.draw_gun = destroyed_draw

        # Delete sprites from lists of sprites
        tanks.remove(self)
        obstacles.remove(self)

        # Increase player's score
        global player_1_score, player_2_score
        if self.number == 1:
            player_1_score += 1
        if self.number == 2:
            player_2_score += 1

    def draw_body(self, surface):
        # Function for drawing tank's body
        surface.blit(self.body, self.rect)

    def draw_gun(self, surface):
        # Function for drawing tank's gun
        surface.blit(self.gun, self.gun_rect)

    def fire(self):
        # Fire function

        # Check if tank isn't destroyed and gun reloaded
        if not self.destroyed and self.reload_frames == 0:
            # Tank reloading switched to off
            self.reload_frames = self.orig_reload_frames

            # Calculate bullet's coordinates
            x = self.rect.center[0] - 5 - sin(self.gun_angle) * 40
            y = self.rect.center[1] - 5 - cos(self.gun_angle) * 40
            self.bullets.append(
                Bullet(
                    [x, y],
                    self.bullet_speed,
                    270 - self.gun_angle,
                    self.color
                )
            )

            # Play shot sound
            SHOT_SOUND.play()


class Block(pygame.sprite.Sprite):
    # Block class
    def __init__(self, pos, *groups):
        # Function of block initialization
        super().__init__(groups)
        self.image = load_image('block.png')
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = pos[0] * self.rect[2], pos[1] * self.rect[3]


class Bullet(pygame.sprite.Sprite):
    # Bullet class

    def __init__(self, pos, v, vector, color):
        # Function of bullet initialization
        super().__init__(bullets)

        # Calculate velocity of bullet
        self.v = v
        self.v_x = v * cos(vector)
        self.v_y = v * sin(vector)

        self.pos = pos
        self.vector = vector

        # Create bullet's image and bullet's rectangle
        self.image = pygame.transform.rotate(
            load_image(f'bullet_{color}.png', -1), 270 - vector
        )

        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = self.pos

    def update(self):
        # Function for updating bullet with new frame

        # Update bullet's coordinates
        self.pos[0] += self.v_x / FPS
        self.pos[1] += self.v_y / FPS
        self.rect.x, self.rect.y = self.pos

        # Check if bullet collides with blocks
        if pygame.sprite.spritecollideany(self, blocks):
            # Destroy bullet
            self.destroy()

            # Play muted boom sound
            BOOM_SOUND.set_volume(0.1)
            BOOM_SOUND.play()

            # Start explosion animation
            Explosion(self.rect.center, 0.2)

        # Check if bullet collides with other bullets
        bullet_collide = pygame.sprite.spritecollide(self, bullets, False)
        if self in bullet_collide:
            bullet_collide.remove(self)

        # If bullet collides with other bullets
        if bullet_collide:
            # Destroy bullets
            bullet_collide[0].destroy()
            self.destroy()

            # Play muted boom sound
            BOOM_SOUND.set_volume(0.2)
            BOOM_SOUND.play()

            # Start explosion animation
            Explosion(self.rect.center, 0.3)

    def destroy(self):
        # Function of bullet destoroying
        bullets.remove(self)

    def draw(self, screen):
        # Function of bullet drawing
        screen.blit(self.image, self.rect)


class Explosion(pygame.sprite.Sprite):
    # Explosion animation class

    def __init__(self, center, size):
        # Explosion animation initialization
        super(Explosion, self).__init__(booms)

        # Create list of animation images with their editing with ratio "size"
        self.explosion_anim = [pygame.transform.scale(load_image(f'explosion ({i + 1}).png', -1), (
            list(map(lambda s: int(s * size),
                     load_image(f'explosion ({i + 1}).png', -1).get_rect()[2:])))) for i in range(9)]

        # Create image of animation and rectangle
        self.image = self.explosion_anim[0]
        self.rect = self.image.get_rect()
        self.rect.center = center

        # Set frames for animation
        self.frame = 0
        self.last_update = pygame.time.get_ticks()
        self.frame_rate = 50
        self.killed = False

    def update(self):
        # Function for animation updating
        if not self.killed:
            # Get number of current frame
            now = pygame.time.get_ticks()
            # Check if time from last frame has passed definitive time
            if now - self.last_update > self.frame_rate:
                self.last_update = now
                self.frame += 1

                # If current frame is last
                if self.frame == len(self.explosion_anim):
                    # Destroy animation
                    self.killed = True
                    booms.remove(self)
                else:
                    # Draw next frame
                    center = self.rect.center
                    self.image = self.explosion_anim[self.frame]
                    self.rect = self.image.get_rect()
                    self.rect.center = center


# Create borders
borders = pygame.sprite.Group()

Border(0, height, width, height, 1)
Border(0, 0, width, 0, 0)
Border(width, 0, width, height, 1)
Border(0, 0, 0, height, 0)

# Dicts with settings of keyboards for players
PLAYER_1_KEYS = {
    pygame.K_w: 'move/up',
    pygame.K_a: 'move/left',
    pygame.K_s: 'move/down',
    pygame.K_d: 'move/right',
    pygame.K_r: 'rotate_gun/true',
    pygame.K_t: 'rotate_gun/false',
    pygame.K_SPACE: 'fire/'
}

PLAYER_2_KEYS = {
    pygame.K_UP: 'move/up',
    pygame.K_LEFT: 'move/left',
    pygame.K_DOWN: 'move/down',
    pygame.K_RIGHT: 'move/right',
    pygame.K_KP_DIVIDE: 'rotate_gun/true',
    pygame.K_KP_MULTIPLY: 'rotate_gun/false',
    pygame.K_KP0: 'fire/'
}

# List of commands, which removing when key pushing
REMOVE_COMMANDS = [
    'fire/',
]


def terminate():
    # Function of game closing
    pygame.quit()
    sys.exit()


def new_match():
    # Function of starting new match

    RELOAD_SOUND.play()

    # Zeroing of player's counts
    global player_1_score, player_2_score
    player_1_score = 0
    player_2_score = 0
    new_round()


def new_round():
    # Function of starting new round
    global all_sprites, obstacles, booms, tanks, bullets, blocks

    # Variable for check if now is pause
    pause = False

    # Get random level name
    level_name = random.choice(get_level_list())

    # Create empty lists of sprites
    all_sprites = pygame.sprite.Group()
    obstacles = pygame.sprite.Group()
    booms = pygame.sprite.Group()
    tanks = pygame.sprite.Group()
    bullets = pygame.sprite.Group()
    blocks = pygame.sprite.Group()

    # Load levels
    level = load_level(level_name)

    # Load blocks by level scheme
    for y in range(-1, len(level)):
        line = level[y]
        for x in range(len(line)):
            if line[x] == '*':
                Block([x, y], blocks, all_sprites, obstacles)
            elif line[x] == '1':
                tank_1 = Tank(
                    [12.5 + x * 75, 12.5 + y * 75],
                    COLORS[0],
                    2,
                    tanks,
                    obstacles,
                    all_sprites
                )
            elif line[x] == '2':
                tank_2 = Tank(
                    [12.5 + x * 75, 12.5 + y * 75],
                    COLORS[1],
                    1,
                    tanks,
                    obstacles,
                    all_sprites
                )

    # Create list for pushed buttons
    button_lst = []

    # Main cycle of game
    while True:
        # Fill screen by bright-blue color
        screen.fill((125, 200, 255))

        keyup_lst = []

        # Get events
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                # Close game
                terminate()
            if event.type == pygame.KEYDOWN:
                # Add buttons to pushed buttons list
                button_lst.append(event.key)
            if event.type == pygame.KEYUP:
                if event.key in button_lst:
                    # Delete button from pushed buttons list
                    button_lst.remove(event.key)
                else:
                    # Add pushed button to delete list
                    keyup_lst.append(event.key)

        # Delete buttons from pushed button list by delete list
        for key in keyup_lst:
            if key in button_lst:
                button_lst.remove(key)

        # Check pause
        if not pause:

            # Performing actions by pushed buttons list
            for i in button_lst[::-1]:
                if i in PLAYER_1_KEYS.keys():
                    command = PLAYER_1_KEYS[i]
                    tank_1.action(command)
                    if command in REMOVE_COMMANDS:
                        button_lst.remove(i)
                elif i in PLAYER_2_KEYS.keys():
                    command = PLAYER_2_KEYS[i]
                    tank_2.action(command)
                    if command in REMOVE_COMMANDS:
                        button_lst.remove(i)
                elif i == pygame.K_ESCAPE:
                    button_lst.remove(i)
                    start_screen()
                elif i == pygame.K_p:
                    pause = not pause
                    button_lst.remove(i)

            # Start function for new round if one of tanks is destroyed
            tank_1.check_destroy()
            tank_2.check_destroy()

            # Update sprites
            tanks.update()
            bullets.update()
            booms.update()
        else:
            # If pause, check P button is pressed to start game
            for i in button_lst:
                if i == pygame.K_p:
                    pause = not pause
                    button_lst.remove(i)

        # Sprites drawing
        blocks.draw(screen)
        for i in bullets.sprites():
            i.draw(screen)
        for i in tanks.sprites():
            i.draw_body(screen)
        booms.draw(screen)
        for i in tanks.sprites():
            i.draw_gun(screen)

        # Create and draw text of score
        font = pygame.font.Font(None, 60)
        players_count_text = font.render(
            str(player_1_score) + '    ' + str(player_2_score),
            1,
            pygame.Color('white')
        )
        text_rect = players_count_text.get_rect(center=[SCREEN_SIZE[0] // 2, 30])
        screen.blit(players_count_text, text_rect)

        clock.tick(FPS)
        pygame.display.flip()


def start_screen():
    # Function of start screen

    # Play start screen music
    MUSIC.play(-1)

    # Text, which drawing in start screen
    intro_text = ["SquareTanks",
                  "Байрамов Азамат",
                  " ",
                  "В игре вам предстоит сражаться",
                  "на танках. Игра рассчитана для",
                  "двоих игроков за одним",
                  "компьютером. ",
                  " ",
                  "Управление в игре",
                  "Движение - WASD и Стрелочки",
                  "Поворот башни - RT и /*(NUM PAD)",
                  "Огонь - Пробел и 0(NUM PAD)",
                  "Пауза - P",
                  "Выход в главное меню - Esc",
                  " ",
                  "Для начала игры нажмите любую клавишу(кроме Esc)",
                  "Для выхода из игры нажмите Esc",
                  ]

    # Draw text
    fon = pygame.transform.scale(load_image('fon.png'), SCREEN_SIZE)
    screen.blit(fon, (0, 0))
    font = pygame.font.Font(None, 30)
    text_coord = 0
    for line in intro_text:
        string_rendered = font.render(line, 1, pygame.Color('black'))
        intro_rect = string_rendered.get_rect()
        text_coord += 10
        intro_rect.top = text_coord
        intro_rect.x = 10
        text_coord += intro_rect.height
        screen.blit(string_rendered, intro_rect)

    # Start screen cycle
    while True:
        # Get events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Close game
                terminate()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Close game
                    terminate()
                else:
                    # Stop music
                    MUSIC.stop()
                    # Start new match
                    new_match()

        clock.tick(FPS)
        pygame.display.flip()


if __name__ == '__main__':
    start_screen()
