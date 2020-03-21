#! /usr/bin/env python3

import math
import os
from random import randint
from collections import deque
import random
import pygame
from pygame.locals import *
import threading
import socket
import time
import random
from _thread import start_new_thread
import operator

# globalVariables

score = 0
listofplayers = []
udp_port = 10000
score_board = {}
xxx = random.randint(1024, 65535)

ME = socket.getaddrinfo('', xxx, socket.AF_INET, socket.SOCK_STREAM)[-1][-1]
print("ME =", ME)
FPS = 60
ANIMATION_SPEED = 0.100  # pixels per millisecond
WIN_WIDTH = 284 * 2  # BG image size: 284x512 px; tiled twice
WIN_HEIGHT = 512


# functions
def udp_discovery():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_sock.settimeout(0.5)
    udp_sock.bind(("", udp_port))
    message = b"client is connected: " + str(xxx).encode()
    while True:
        udp_sock.sendto(message, ("<broadcast>", udp_port))
        #print('broadcast sent')
        while True:
            try:
                msg, addr = udp_sock.recvfrom(1024)
                print(msg.decode(), addr)
                portt = int(msg.decode().split(" ")[-1])
                if (addr[0], portt) not in listofplayers:
                    listofplayers.append((addr[0], portt))
            except socket.timeout:
                break
        print('list of players: ', listofplayers)
        time.sleep(5)


def update_scoreboard():
    while True:
        recv()
        send()
        score_board[ME[0]] = score


def recv():
    while True:
        try:
            #print("gowa try")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.bind(ME)
            sock.listen(5)
            client_sock, client_addr = sock.accept()
            print("connected to:", client_addr)
            score_board[client_addr[0]] = int(client_sock.recv(1024).decode())
            client_sock.shutdown(socket.SHUT_RDWR)
            client_sock.close()
        except socket.timeout:
           # print("timeout, no data sent")
            break


def send():
    for player in listofplayers.copy():
        if player != ME:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect(player)
                sock.sendall(str(score).encode())
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()
                #print("SUCCESSFULL !!! ")
            except socket.timeout:
                pass
                #print("did not connect")


def countdown(t):
    while t:
        mins, secs = divmod(t, 5)
        timeformat = '{:02d}:{:02d}'.format(mins, secs)
        print(timeformat, end='\r')
        time.sleep(1)
        t -= 1
    winner = max(score_board.items(), key=operator.itemgetter(1))[0]
    print("WINNER WINNER CHICKEN DINNER:", winner)
    print('Goodbye!\n\n\n\n\n')
    os._exit(1)


def show_scoreboard():
    while True:
        print('score board:', score_board)
       # print('MY SCORE IS ', score)
        time.sleep(2)


class Bird(pygame.sprite.Sprite):
    WIDTH = HEIGHT = 32
    SINK_SPEED = 0.18
    CLIMB_SPEED = 0.15
    CLIMB_DURATION = 333.3

    def __init__(self, x, y, msec_to_climb, images):

        super(Bird, self).__init__()
        self.x, self.y = x, y
        self.msec_to_climb = msec_to_climb
        self._img_wingup, self._img_wingdown = images
        self._mask_wingup = pygame.mask.from_surface(self._img_wingup)
        self._mask_wingdown = pygame.mask.from_surface(self._img_wingdown)

    def update(self, delta_frames=1):

        if self.msec_to_climb > 0:
            frac_climb_done = 1 - self.msec_to_climb / Bird.CLIMB_DURATION
            self.y -= (Bird.CLIMB_SPEED * frames_to_msec(delta_frames) *
                       (1 - math.cos(frac_climb_done * math.pi)))
            self.msec_to_climb -= frames_to_msec(delta_frames)
        else:
            self.y += Bird.SINK_SPEED * frames_to_msec(delta_frames)

    @property
    def image(self):

        if pygame.time.get_ticks() % 500 >= 250:
            return self._img_wingup
        else:
            return self._img_wingdown

    @property
    def mask(self):

        if pygame.time.get_ticks() % 500 >= 250:
            return self._mask_wingup
        else:
            return self._mask_wingdown

    @property
    def rect(self):
        """Get the bird's position, width, and height, as a pygame.Rect."""
        return Rect(self.x, self.y, Bird.WIDTH, Bird.HEIGHT)


class PipePair(pygame.sprite.Sprite):
    WIDTH = 80
    PIECE_HEIGHT = 32
    ADD_INTERVAL = 3000

    def __init__(self, pipe_end_img, pipe_body_img):

        self.x = float(WIN_WIDTH - 1)
        self.score_counted = False

        self.image = pygame.Surface((PipePair.WIDTH, WIN_HEIGHT), SRCALPHA)
        self.image.convert()  # speeds up blitting
        self.image.fill((0, 0, 0, 0))
        total_pipe_body_pieces = int(
            (WIN_HEIGHT -  # fill window from top to bottom
             3 * Bird.HEIGHT -  # make room for bird to fit through
             3 * PipePair.PIECE_HEIGHT) /  # 2 end pieces + 1 body piece
            PipePair.PIECE_HEIGHT  # to get number of pipe pieces
        )
        self.bottom_pieces = randint(1, total_pipe_body_pieces)
        self.top_pieces = total_pipe_body_pieces - self.bottom_pieces

        # bottom pipe
        for i in range(1, self.bottom_pieces + 1):
            piece_pos = (0, WIN_HEIGHT - i * PipePair.PIECE_HEIGHT)
            self.image.blit(pipe_body_img, piece_pos)
        bottom_pipe_end_y = WIN_HEIGHT - self.bottom_height_px
        bottom_end_piece_pos = (0, bottom_pipe_end_y - PipePair.PIECE_HEIGHT)
        self.image.blit(pipe_end_img, bottom_end_piece_pos)

        # top pipe
        for i in range(self.top_pieces):
            self.image.blit(pipe_body_img, (0, i * PipePair.PIECE_HEIGHT))
        top_pipe_end_y = self.top_height_px
        self.image.blit(pipe_end_img, (0, top_pipe_end_y))

        # compensate for added end pieces
        self.top_pieces += 1
        self.bottom_pieces += 1

        # for collision detection
        self.mask = pygame.mask.from_surface(self.image)

    @property
    def top_height_px(self):
        return self.top_pieces * PipePair.PIECE_HEIGHT

    @property
    def bottom_height_px(self):
        return self.bottom_pieces * PipePair.PIECE_HEIGHT

    @property
    def visible(self):

        return -PipePair.WIDTH < self.x < WIN_WIDTH

    @property
    def rect(self):

        return Rect(self.x, 0, PipePair.WIDTH, PipePair.PIECE_HEIGHT)

    def update(self, delta_frames=1):

        self.x -= ANIMATION_SPEED * frames_to_msec(delta_frames)

    def collides_with(self, bird):

        return pygame.sprite.collide_mask(self, bird)


def load_images():
    def load_image(img_file_name):
        file_name = os.path.join('.', 'images', img_file_name)
        img = pygame.image.load(file_name)
        img.convert()
        return img

    return {'background': load_image('background.png'),
            'pipe-end': load_image('pipe_end.png'),
            'pipe-body': load_image('pipe_body.png'),
            # images for animating the flapping bird -- animated GIFs are
            # not supported in pygame
            'bird-wingup': load_image('bird_wing_up.png'),
            'bird-wingdown': load_image('bird_wing_down.png')}


def frames_to_msec(frames, fps=FPS):
    return 1000.0 * frames / fps


def msec_to_frames(milliseconds, fps=FPS):
    return fps * milliseconds / 1000.0


def main():
    pygame.init()

    display_surface = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
    pygame.display.set_caption('Pygame Flappy Bird')

    clock = pygame.time.Clock()
    score_font = pygame.font.SysFont(None, 32, bold=True)  # default font
    images = load_images()

    # the bird stays in the same x position, so bird.x is a constant
    # center bird on screen
    bird = Bird(50, int(WIN_HEIGHT / 2 - Bird.HEIGHT / 2), 2,
                (images['bird-wingup'], images['bird-wingdown']))

    pipes = deque()

    frame_clock = 0  # this counter is only incremented if the game isn't paused
    global score
    score = 0
    done = paused = False
    while not done:
        clock.tick(FPS)

        # Handle this 'manually'.  If we used pygame.time.set_timer(),
        # pipe addition would be messed up when paused.
        if not (paused or frame_clock % msec_to_frames(PipePair.ADD_INTERVAL)):
            pp = PipePair(images['pipe-end'], images['pipe-body'])
            pipes.append(pp)

        for e in pygame.event.get():
            if e.type == QUIT or (e.type == KEYUP and e.key == K_ESCAPE):
                done = True
                break
            elif e.type == KEYUP and e.key in (K_PAUSE, K_p):
                paused = not paused
            elif e.type == MOUSEBUTTONUP or (e.type == KEYUP and
                                             e.key in (K_UP, K_RETURN, K_SPACE)):
                bird.msec_to_climb = Bird.CLIMB_DURATION

        if paused:
            continue  # don't draw anything

        # check for collisions
        pipe_collision = any(p.collides_with(bird) for p in pipes)
        if pipe_collision or 0 >= bird.y or bird.y >= WIN_HEIGHT - Bird.HEIGHT:
            done = True

        for x in (0, WIN_WIDTH / 2):
            display_surface.blit(images['background'], (x, 0))

        while pipes and not pipes[0].visible:
            pipes.popleft()

        for p in pipes:
            p.update()
            display_surface.blit(p.image, p.rect)

        bird.update()
        display_surface.blit(bird.image, bird.rect)
        # update and display score
        for p in pipes:
            if p.x + PipePair.WIDTH < bird.x and not p.score_counted:
                score += 1
                # print("MY SCORE is ", score)
                p.score_counted = True

        score_surface = score_font.render(str(score), True, (255, 255, 255))
        score_x = WIN_WIDTH / 2 - score_surface.get_width() / 2
        display_surface.blit(score_surface, (score_x, PipePair.PIECE_HEIGHT))
        # while True:
        #     client_score = sock.recv(1024)
        #     client_score.decode()
        #     print("Server Score is now : %i " % client_score)

        pygame.display.flip()
        frame_clock += 1

    # sending el score

    # send_data=score.encode()
    # conn.send(send_data)

    print('Game over! Score: %i' % score)
    exit()
    pygame.quit()


start_new_thread(udp_discovery, ())
start_new_thread(update_scoreboard, ())
start_new_thread(show_scoreboard, ())
#start_new_thread(countdown, (20, ))
start_new_thread(main, ())

countdown(20)
while True:
    pass

"""
if __name__ == '__main__':
    # If this module had been imported, __name__ would be 'flappybird'.
    # It was executed (e.g. by double-clicking the file), so call main.
    main()
    """
