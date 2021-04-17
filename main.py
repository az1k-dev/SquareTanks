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
        # Функция для передачи команд для танка
        # Параметр command - команда для танка. Передается в виде команда/параметр.

        # Проверка неуничтожения танка
        if not self.destroyed:
            # Разделение входной команды на команду и параметр
            command, parameter = command.split('/')

            # Выполнение команды
            if command == 'move':
                self.move(parameter)
            elif command == 'rotate_gun':
                self.rotate_gun({'true': True, 'false': False}[parameter])
            elif command == 'fire':
                self.fire()

    def update(self):
        # Обновление танка с новым кадром
        if not self.destroyed:
            # Изменение параметра для исключения возможности нескольких движений за ход
            self.not_moved_in_frame = True

            # Изменение изображения танка по направлению танка
            self.body = pygame.transform.rotate(self.body_image, (self.body_angle + 90) % 360)

            # Изменение изображения пушки и прямоугольника по направлению пушки
            self.gun = pygame.transform.rotate(self.gun_image, self.gun_angle)
            self.gun_rect = self.gun.get_rect(center=self.rect.center)

            # Уменьшение количества кадров до перезарядки
            if self.reload_frames > 0:
                self.reload_frames -= 1

            # Получение действующих снарядов кроме своих
            frame_bullets = bullets.copy()
            for i in self.bullets:
                frame_bullets.remove(i)

            # Проверка на пересечение со снарядами
            bullets_collide = pygame.sprite.spritecollideany(self, frame_bullets)
            if bullets_collide:
                # При пересечении снаряд уничтожается и запускается функция по уничтожению танка
                bullets_collide.destroy()
                self.boom()

    def boom(self):
        # Функция по уничтожению танка

        # Воспроизводится звук взрыва
        BOOM_SOUND.set_volume(1)
        BOOM_SOUND.play()

        # Меняется переменная для проверки уничтожения танка
        self.destroyed = True

        # Запускается анимация взрыва
        Explosion(self.rect.center, 1)

        # Создается пустая функция
        def destroyed_draw(surface):
            pass

        # Функции отрисовок меняются на пустую
        self.draw_body = destroyed_draw
        self.draw_gun = destroyed_draw

        # Спрайт удаляется из групп
        tanks.remove(self)
        obstacles.remove(self)

        # Пополняется счет выигравшего танка
        global player_1_count, player_2_count
        if self.number == 1:
            player_1_count += 1
        if self.number == 2:
            player_2_count += 1

    def draw_body(self, surface):
        # Функция отрисовки корпуса танка
        surface.blit(self.body, self.rect)

    def draw_gun(self, surface):
        # Функция отрисовки пушки танка
        surface.blit(self.gun, self.gun_rect)

    def fire(self):
        # Функция выстрела

        # Проверка заряженности оружия танка и неуничтоженности танка
        if not self.destroyed and self.reload_frames == 0:
            # Заряженность танка возвращается к незаряженному
            self.reload_frames = self.orig_reload_frames

            # Вычисляются координаты снарядаи создается снаряд
            x = self.rect.center[0] - 5 - sin(self.gun_angle) * 40
            y = self.rect.center[1] - 5 - cos(self.gun_angle) * 40
            self.bullets.append(Bullet([x, y], self.bullet_speed, 270 - self.gun_angle, self.color))

            # Вопспроизводится звук выстрела
            SHOT_SOUND.play()


class Block(pygame.sprite.Sprite):
    # Класс блока
    def __init__(self, pos, *groups):
        # Функция инициализации блока
        super().__init__(groups)
        self.image = load_image('block.png')
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = pos[0] * self.rect[2], pos[1] * self.rect[3]


class Bullet(pygame.sprite.Sprite):
    # Класс снаряда

    def __init__(self, pos, v, vector, color):
        # Функция инициализации снаряда
        super().__init__(bullets)

        # Вычисление скоростей
        self.v = v
        self.v_x = v * cos(vector)
        self.v_y = v * sin(vector)

        self.pos = pos
        self.vector = vector

        # Создание изображения и прямоугольника спрайта
        self.image = pygame.transform.rotate(load_image(f'bullet_{color}.png', -1),
                                             270 - vector)
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = self.pos

    def update(self):
        # Функция обновления с новым кадром

        # Обновление координат снаряда
        self.pos[0] += self.v_x / FPS
        self.pos[1] += self.v_y / FPS
        self.rect.x, self.rect.y = self.pos

        # Проверка на пересечение с блоками
        if pygame.sprite.spritecollideany(self, blocks):
            # Уничтожаем снаряд
            self.destroy()

            # Воспроизведение звука взрыва с уменьшением звука
            BOOM_SOUND.set_volume(0.1)
            BOOM_SOUND.play()

            # Запускается анимация взрыва
            Explosion(self.rect.center, 0.2)

        # Проверка на столкновение с другими снарядами
        bullet_collide = pygame.sprite.spritecollide(self, bullets, False)
        if self in bullet_collide:
            bullet_collide.remove(self)

        # При столкновении с другими снарядами:
        if bullet_collide:
            # Уничтожаем снаряды
            bullet_collide[0].destroy()
            self.destroy()

            # Воспроизведение звука взрыва с уменьшением звука
            BOOM_SOUND.set_volume(0.2)
            BOOM_SOUND.play()

            # Запускается анимация взрыва
            Explosion(self.rect.center, 0.3)

    def destroy(self):
        # Уничтожение снаряда
        bullets.remove(self)

    def draw(self, screen):
        # Фукция отрисовки снаряда
        screen.blit(self.image, self.rect)


class Explosion(pygame.sprite.Sprite):
    # Класс анимации взрыва

    def __init__(self, center, size):
        # Инициализация класса
        super(Explosion, self).__init__(booms)

        # Создание списка изображений анимации с их изменением на коэффицент size
        self.explosion_anim = [pygame.transform.scale(load_image(f'explosion ({i + 1}).png', -1), (
            list(map(lambda s: int(s * size),
                     load_image(f'explosion ({i + 1}).png', -1).get_rect()[2:])))) for i in range(9)]

        # Создание изображения анимации и прямоугольника
        self.image = self.explosion_anim[0]
        self.rect = self.image.get_rect()
        self.rect.center = center

        # Настройка кадров для анимации
        self.frame = 0
        self.last_update = pygame.time.get_ticks()
        self.frame_rate = 50
        self.killed = False

    def update(self):
        # Обновление анмации
        if not self.killed:
            # Получение номера нынешнего кадра
            now = pygame.time.get_ticks()
            # Проверка на прошествие определенного времени
            if now - self.last_update > self.frame_rate:
                self.last_update = now
                self.frame += 1

                if self.frame == len(self.explosion_anim):
                    # Уничтожение анимации
                    self.killed = True
                    booms.remove(self)
                else:
                    # Отображение следующего изображения
                    center = self.rect.center
                    self.image = self.explosion_anim[self.frame]
                    self.rect = self.image.get_rect()
                    self.rect.center = center


# Создание ограничителей
borders = pygame.sprite.Group()

Border(0, height, width, height, 1)
Border(0, 0, width, 0, 0)
Border(width, 0, width, height, 1)
Border(0, 0, 0, height, 0)

# Словари настроек кнопок игрока 1 и 2
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

# Список команд клавиши которых сбрасываются после нажатия
REMOVE_COMMANDS = [
    'fire/',
]


def terminate():
    # Функция по закрытию программы
    pygame.quit()
    sys.exit()


def new_match():
    # Функция по запуску нового матча

    RELOAD_SOUND.play()

    # Обнуление результатов
    global player_1_count, player_2_count
    player_1_count = 0
    player_2_count = 0
    new_round()


def new_round():
    # Функция по запуску нового раунда
    global all_sprites, obstacles, booms, tanks, bullets, blocks

    # Переменная для проверки паузы
    pause = False

    # Получение случайного названия уровня
    level_name = random.choice(get_level_list())

    # Создание пустых групп спрайтов
    all_sprites = pygame.sprite.Group()
    obstacles = pygame.sprite.Group()
    booms = pygame.sprite.Group()
    tanks = pygame.sprite.Group()
    bullets = pygame.sprite.Group()
    blocks = pygame.sprite.Group()

    # Загрузка уровня
    level = load_level(level_name)

    # Загрузка блоков по уровню
    for y in range(-1, len(level)):
        line = level[y]
        for x in range(len(line)):
            if line[x] == '*':
                Block([x, y], blocks, all_sprites, obstacles)
            elif line[x] == '1':
                tank_1 = Tank([12.5 + x * 75, 12.5 + y * 75], COLORS[0], 2, tanks, obstacles,
                              all_sprites)
            elif line[x] == '2':
                tank_2 = Tank([12.5 + x * 75, 12.5 + y * 75], COLORS[1], 1, tanks, obstacles,
                              all_sprites)

    # Создание списка для хранения нажатых кнопок
    button_lst = []

    # Основной цикл игры
    while True:
        # Заполнение фона голубым цветом
        screen.fill((125, 200, 255))

        keyup_lst = []

        # Получение событий
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                # Выключение программы
                terminate()
            if event.type == pygame.KEYDOWN:
                # Добавление нажатой кнопки в список нажатых кнопок
                button_lst.append(event.key)
            if event.type == pygame.KEYUP:
                if event.key in button_lst:
                    # Удаление нажатой кнопки из списка нажатых кнопок
                    button_lst.remove(event.key)
                else:
                    # Сохранение нажатой кнопки в список удалений
                    keyup_lst.append(event.key)

        # Удаление кнопок из списка основываясь на список удалений
        for key in keyup_lst:
            if key in button_lst:
                button_lst.remove(key)

        # Проверка паузы в игре
        if not pause:

            # Выполнение действий по клавишам
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

            # Запуск функции для запуска нового раунда при уничтожении танков
            tank_1.check_destroy()
            tank_2.check_destroy()

            # Обновление спрайтов
            tanks.update()
            bullets.update()
            booms.update()
        else:
            # Проверка на нажатие кнопки P для продолжения игры
            for i in button_lst:
                if i == pygame.K_p:
                    pause = not pause
                    button_lst.remove(i)

        # Отрисовка спрайтов
        blocks.draw(screen)
        for i in bullets.sprites():
            i.draw(screen)
        for i in tanks.sprites():
            i.draw_body(screen)
        booms.draw(screen)
        for i in tanks.sprites():
            i.draw_gun(screen)

        # Создание и отрисовка текста счета игроков
        font = pygame.font.Font(None, 60)
        players_count_text = font.render(str(player_1_count) + '    ' + str(player_2_count), 1,
                                         pygame.Color('white'))
        text_rect = players_count_text.get_rect(center=[SCREEN_SIZE[0] // 2, 30])
        screen.blit(players_count_text, text_rect)

        clock.tick(FPS)
        pygame.display.flip()


def start_screen():
    # Функция отображения главного экрана

    # Воспроизводится звук
    MUSIC.play(-1)

    # Текст, который отрисовывается на главном экране
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

    # Отрисовка текста
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

    # Цикл главного экрана
    while True:
        # Получение событий
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Выключение программы
                terminate()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Выключение программы
                    terminate()
                else:
                    # Остановка музыки
                    MUSIC.stop()
                    # Запуск нового матча
                    new_match()

        clock.tick(FPS)
        pygame.display.flip()


if __name__ == '__main__':
    start_screen()
