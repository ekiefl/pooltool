#! /usr/bin/env python

import pooltool.constants as c
import pooltool.events as e
from pooltool.games.datatypes import Game
from pooltool.layouts import SnookerRack
from pooltool.objects.ball.datatypes import Ball

RED_BALLS = ["red"]
RED_BALLS = ["red" + str(i) for i in range(1, 16)]

COLORED_BALLS = ["yellow", "green", "brown", "blue", "pink", "black"]

POINTS = {  
    "white" : -4,
    "red"   : 1,
    "yellow": 2, 
    "green" : 3, 
    "brown" : 4, 
    "blue"  : 5, 
    "pink"  : 6, 
    "black" : 7 
    }
for i in range(1, 16):
    POINTS["red" + str(i)] = 1 

class Snooker(Game):
    rack = SnookerRack

    def __init__(self):
        # TODO how to track call ball?
        self.is_call_ball = False
        self.is_call_pocket = False

        self.hit_first = None
        self.pottedBalls = []   # Dictionary to store potted balls
        self.colorCount = 0     # Counter to cycle through COLORED_BALLS Dictionary
        self.expected = RED_BALLS
        Game.__init__(self)

        self.create_players(2)

        for player in self.players:
            player.can_cue = ["white"]

    def start(self, shot):
        self.active_player.ball_in_hand = ["white"]

    def get_initial_cueing_ball(self, balls):
        return balls["white"]

    def highestBallHit(self, shot):
        cue_events = e.filter_ball(shot.events, shot.balls["white"].id)
        cue_contacts = e.filter_type(cue_events, e.EventType.BALL_BALL)
        if not len(cue_contacts):
            hit_balls = []
            for collision in cue_contacts: 
                if collision.agents[1].id == "white":
                    hit_balls.append(POINTS[collision.agents[0].id])
                elif collision.agents[0].id == "white":
                    hit_balls.append(POINTS[collision.agents[1].id])

            return max(hit_balls) if hit_balls else 0
        return 0

    def highestBallPotted(self, shot):
        pocket_events = e.filter_type(shot.events, e.EventType.BALL_POCKET)
        potted_balls = [POINTS[event.agents[0].id] for event in pocket_events]
        return max(potted_balls) if potted_balls else 0

    def award_points(self, shot):
        self.shot_info["points"] = {player: 0 for player in self.players}
        points = self.shot_info["points"][self.active_player] 

        # subtract points for a fault
        if not self.shot_info["is_legal"]:
            hbp = self.highestBallPotted(shot)
            hbh = self.highestBallHit(shot)
            # TODO how to implement situation when expected ball not potted
            if max(hbp, hbh) <= 4:
                points -= 4
            else:
                points -= max(hbp, hbh)

            self.log.add_msg("Points : " + str(points))  

        # add points for sussefully potted ball(s)
        else:
            pocket_events = e.filter_type(shot.events, e.EventType.BALL_POCKET)
            potted_balls = [event.agents[0] for event in pocket_events]
            for ball in potted_balls:
                points += POINTS[ball.id]
                self.log.add_msg("Potted ball :" + ball.id)  
                self.log.add_msg("Points : " + str(points))  

        self.shot_info["points"][self.active_player] = points

    def decide_winner(self, shot):
        if self.players[0].points == self.players[1].points:
            self.winner = None
            self.tie = True
        else:
            self.winner = max(self.players, key=lambda x: x.points)

    def award_ball_in_hand(self, shot):
        if not self.shot_info["is_legal"]:
            self.shot_info["ball_in_hand"] = ["white"]
            # Place 'white' ball into the semi circle
            # Default position halfway between brown and green
            if self.is_cue_pocketed(shot):
                x,y,r = self.getRespotPosition("white", shot)
                self.respot(shot, "white", x,y,r)
            # TODO for now white ball after a fault will remain on its position
            # but in real game player has a chance to respot white 
        else:
            self.shot_info["ball_in_hand"] = None

    def respot_balls(self, shot):
        pocket_events = e.filter_type(shot.events, e.EventType.BALL_POCKET)
        pocketed_balls = [event.agents[0] for event in pocket_events]
        for ball in pocketed_balls:
            # respot colored balls until all red balls are potted
            # red balls are not respoted
            if self.getCountPottedBalls("red") != 15 and ball.id[:3] != "red":
                x,y,r = self.getRespotPosition(ball.id, shot)
                self.respot(shot, ball.id, x,y,r)
            else:
                # respot wrongly pocketed color ball after all 15 reds are pocketed
                if not self.shot_info["is_legal"]:
                    x,y,r = self.getRespotPosition(ball.id, shot)
                    self.respot(shot, ball.id, x,y,r)

    # TODO maybe can be implemented as dictionary 
    # TODO what to do if position is already taken by another ball
    def getRespotPosition(self, color, shot):
        x,y,r = None,None,None

        if color == "yellow":
            x,y,r = shot.table.w * 2/3, shot.table.l / 5, shot.balls["yellow"].params.R
        elif color == "green":
            x,y,r = shot.table.w * 2/3, shot.table.l / 5, shot.balls["green"].params.R
        elif color == "brown":
            x,y,r = shot.table.w / 2, shot.table.l / 5, shot.balls["brown"].params.R
        elif color == "blue":
            x,y,r = shot.table.w / 2, shot.table.l / 2, shot.balls["blue"].params.R
        elif color == "pink":
            x,y,r = shot.table.w / 2, shot.table.l * 3/4, shot.balls["pink"].params.R
        elif color == "black":
            x,y,r = shot.table.w / 2, shot.table.l * 10/11, shot.balls["black"].params.R
        elif color == "white":
            x,y,r = shot.table.w * 7/12, shot.table.l / 5, shot.balls["white"].params.R

        return x,y,r

    def is_turn_over(self, shot):
        if not self.shot_info["is_legal"]:
            return True

        pocket_events = e.filter_type(shot.events, e.EventType.BALL_POCKET)
        balls_potted = [event.agents[0] for event in pocket_events]

        if balls_potted:
            # Update expected balls targets for the next shot
            # check if potted ball was "red"
            if balls_potted[0].id in RED_BALLS:
                self.expected = COLORED_BALLS
                # If shot was legal only several red balls are allowed. Log potting event(s)
                for ball in balls_potted:
                    # Add red ball(s) to the collection of the potted balls
                    self.pottedBalls.append(ball)
                    self.log.add_msg(f"Ball potted: {ball.id}", sentiment="good")

            # check if potted ball was colored and still red balls are left
            elif balls_potted[0].id in COLORED_BALLS and self.getCountPottedBalls("red") != 15:
                self.expected = RED_BALLS
            # check if potted ball was colored and no red balls are left
            elif balls_potted[0].id in COLORED_BALLS and self.getCountPottedBalls("red") == 15:
                # Now we need to follow color sequence
                self.expected = [COLORED_BALLS[self.colorCount]]
                self.colorCount += 1
                # Add colored ball to the collection of the potted balls
                self.pottedBalls.append(ball)
                self.log.add_msg(f"Ball potted: {ball.id}", sentiment="good")
            return False

        # If no ball was potted in this shot restore expected target
        # always reset target to red 
        if self.getCountPottedBalls("red") != 15:
            self.expected = RED_BALLS
        # if all red are potted and yellow not yet potted set target to yellow
        # TODO check if this is right
        if self.getCountPottedBalls("red") == 15 and self.getCountPottedBalls("yellow") == 0: 
            self.expected = ["yellow"]

        return True

    def getCountPottedBalls(self, color):
        # compare only first 3 leters of the color. 
        # For RED it should return values 0-15. For COLORED balls 0-1
        return len( [ball for ball in self.pottedBalls if ball.id[:3] == color[:3]] )

    def is_game_over(self, shot):
        pocket_events = e.filter_type(shot.events, e.EventType.BALL_POCKET)
        balls_potted = [event.agents[0].id for event in pocket_events]

        # Last pocketed ball is 'black' and legally pocketed
        if len(balls_potted) == 1 and self.shot_info["is_legal"]:
            if balls_potted[0] == 'black':
                return True
        return False

    # Return number of hits any ball hit any cushion
    def ball_hit_cushion(self, shot):
        cushion_events = e.filter_type(
            shot.events,
            [e.EventType.BALL_LINEAR_CUSHION, e.EventType.BALL_CIRCULAR_CUSHION],
        )

        return set([event.agents[0].id for event in cushion_events])

    # Return number of hits cue ball hit cushion
    # TODO not used method
    def cue_ball_hit_cushion(self, shot):
        cue_ball = [ball.id for ball in shot.balls.values() if ball.id == "white"]

        cushion_events = e.filter_type(
            shot.events,
            [e.EventType.BALL_LINEAR_CUSHION, e.EventType.BALL_CIRCULAR_CUSHION],
        )
        cue_ball_cushion_events = e.filter_ball(cushion_events, cue_ball)

        return set([event.agents[0].id for event in cue_ball_cushion_events])

    # Return number of hits any color ball hit cushion
    # TODO not used method
    def colored_balls_that_hit_cushion(self, shot):
        colored_balls = [ball.id for ball in shot.balls.values() if ball.id != "white"]

        cushion_events = e.filter_type(
            shot.events,
            [e.EventType.BALL_LINEAR_CUSHION, e.EventType.BALL_CIRCULAR_CUSHION],
        )
        colored_ball_cushion_events = e.filter_ball(cushion_events, colored_balls)

        return set([event.agents[0].id for event in colored_ball_cushion_events])

    def is_cue_pocketed(self, shot):
        return shot.balls["white"].state == c.pocketed

    # Check if first ball hit event was with expected ball
    def is_expected_ball_hit_first(self, shot):
        cue_events = e.filter_ball(shot.events, shot.balls["white"].id)
        first_contact = e.filter_type(cue_events, e.EventType.BALL_BALL)[0]

        ball1, ball2 = first_contact.agents
        self.hit_first = ball1.id if ball1.id != "white" else ball2.id        

        return True if (self.hit_first in self.expected) else False

    # Check if expected ball pocketed
    def is_expected_ball_pocketed(self, shot):
        result = False
        # List all pocketed balls
        pocket_events = e.filter_type(shot.events, e.EventType.BALL_POCKET)
        pocketed_balls_ids = [event.agents[0].id for event in pocket_events]

        # Check if expected ball was pocketed, and it is the only color pocketed
        # Ex: ["red1", "red2"] -> OK
        #     ["blue"]       -> OK
        #     ["red1", "red2", "blue"] -> NOK
        if pocketed_balls_ids:
            if pocketed_balls_ids[0] in self.expected and \
                pocketed_balls_ids.count(pocketed_balls_ids[0]) == len(pocketed_balls_ids):
                result = True
    
        return result

    def legality(self, shot):
        """Returns whether or not a shot is legal, and the reason"""
        reason = None

        pocket_events = e.filter_type(shot.events, e.EventType.BALL_POCKET)
        potted_balls = [event.agents[0].id for event in pocket_events]

        if not self.is_expected_ball_hit_first(shot):
            reason = "Not expected ball hit first. Expected :" + str(self.expected) + "; Hit first :" + self.hit_first
        elif not self.is_expected_ball_pocketed(shot) and len(potted_balls) != 0:
            reason = "Not expected ball potted. Expected :" + str(self.expected) + "; Potted :" + str(potted_balls)
        elif self.is_cue_pocketed(shot):
            reason = "Cue ball in a pocket!"
        elif not self.ball_hit_cushion(shot):
            reason = "No cushion contacted after a shot"
        #elif not self.is_shot_called(shot):
        #    reason = "No shot called!"

        return (True, reason) if not reason else (False, reason)
    
    # TODO how to implement called pockets?
    def is_shot_called(self, shot):
        if self.shot_number == 0:
            return True

        if self.ball_call is None or self.pocket_call is None:
            return False

        return True
