#! /usr/bin/env python

import psim.ani
import pygame
import pygame.gfxdraw

from psim.ani import px_to_d, d_to_px

# Import pygame.locals for easier access to key coordinates
from pygame.locals import (
    K_SPACE,
    K_ESCAPE,
    K_DOWN,
    K_UP,
    K_RIGHT,
    K_LEFT,
    KEYDOWN,
    KEYUP,
    QUIT,
)


class Ball(pygame.sprite.Sprite):
    def __init__(self, ball, scale):
        """A ball sprite

        Parameters
        ==========
        ball : psim.objects.Ball
        """
        self.scale = scale
        self._ball = ball
        self.radius = d_to_px(ball.R, self.scale)
        self.df = ball.as_dataframe()

        super(Ball, self).__init__()

        # See https://www.reddit.com/r/pygame/comments/6v9os5/how_to_draw_a_sprite_with_a_circular_shape/
        # for anti-aliased version if you don't like this later
        self.surf = pygame.Surface((self.radius*2, self.radius*2), pygame.SRCALPHA)
        pygame.draw.circle(self.surf, (255,255,255), (self.radius, self.radius), self.radius)
        self.rect = self.surf.get_rect()

        self.update(frame=0)


    def update(self, frame):
        self.rect.center = (
            d_to_px(self.df['rx'].iloc[frame], self.scale),
            d_to_px(self.df['ry'].iloc[frame], self.scale),
        )


class AnimateShot(object):
    def __init__(self, shot, size=psim.ani.MAX_SCREEN):
        """Animate a shot in pygame

        Parameters
        ==========
        shot : psim.engine.ShotSimulation

        size : int
            size in pixels of largest dimension of screen
        """

        self.shot = shot
        self.table = shot.table
        self.balls = shot.balls
        self.times = shot.get_time_array()
        self.num_frames = len(self.times)

        # Ratio of pixel to table dimensions
        self.scale = size / max([self.table.w, self.table.l])

        pygame.init()

        screen_width = d_to_px(self.scale, self.table.w)
        screen_height = d_to_px(self.scale, self.table.l)
        self.screen = pygame.display.set_mode((screen_width, screen_height))

        # Create ball sprites
        self.ball_sprites = pygame.sprite.Group()
        for ball_id, ball in self.balls.items():
            self.ball_sprites.add(Ball(ball, self.scale))

        self.clock = pygame.time.Clock()
        self.fps = self.get_fps()


    def get_fps(self):
        return 1/(self.times[-1] - self.times[-2])


    def display(self):
        # Flip vertical axis so origin is bottom left
        display_surface = pygame.display.get_surface()
        display_surface.blit(pygame.transform.flip(display_surface, False, True), dest=(0, 0))

        # Update the display
        pygame.display.flip()



    def start(self):
        running = True
        paused = False
        frame_forward = False
        frame_backward = False
        increase_speed = False
        decrease_speed = False
        counter = 0

        while running:
            self.screen.fill((100, 255, 100))

            # for loop through the event queue
            for event in pygame.event.get():
                # Check for KEYDOWN event
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        running = False
                    elif event.key == K_SPACE:
                        paused = not paused
                    elif event.key == K_DOWN:
                        decrease_speed = True
                    elif event.key == K_UP:
                        increase_speed = True
                    elif event.key == K_RIGHT:
                        paused = True
                        frame_forward = True
                    elif event.key == K_LEFT:
                        paused = True
                        frame_backward = True
                elif event.type == KEYUP:
                    if event.key == K_DOWN:
                        decrease_speed = False
                    elif event.key == K_UP:
                        increase_speed = False
                    if event.key == K_RIGHT:
                        frame_forward = False
                    elif event.key == K_LEFT:
                        frame_backward = False
                elif event.type == QUIT:
                    running = False

            # Draw the balls on the screen
            for ball in self.ball_sprites:
                self.screen.blit(ball.surf, ball.rect)

            self.display()

            if not paused:
                # Draw the balls on the screen
                for ball in self.ball_sprites:
                    ball.update(frame=counter)
                counter += 1

            elif frame_backward:
                for ball in self.ball_sprites:
                    ball.update(frame=counter)
                counter -= 1

            elif frame_forward:
                for ball in self.ball_sprites:
                    ball.update(frame=counter)
                counter += 1

            if counter == self.num_frames:
                # Restart animation
                counter = 0

            if decrease_speed:
                self.fps = max([1, self.fps*0.96])
            elif increase_speed:
                self.fps = min([100, self.fps*1.04])

            self.clock.tick(self.fps)


