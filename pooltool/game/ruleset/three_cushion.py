#! /usr/bin/env python

import pooltool.constants as c
from pooltool.error import ConfigError
from pooltool.game.ruleset.datatypes import Game
from pooltool.layouts import ThreeCushionRack


class ThreeCushion(Game):
    rack = ThreeCushionRack

    def __init__(self):
        self.points_to_win = 20
        self.is_call_ball = False
        self.is_call_pocket = False
        Game.__init__(self)
        self.create_players(2)

    def start(self, shot):
        self.players[0].can_cue = ["white"]
        self.players[0].target_balls = ["yellow", "red"]
        self.players[1].can_cue = ["yellow"]
        self.players[1].target_balls = ["white", "red"]

    def get_initial_cueing_ball(self, balls):
        return balls["white"]

    def award_points(self, shot):
        self.shot_info["points"] = {player: 0 for player in self.players}

        if not self.shot_info["is_legal"]:
            return

        if is_hit(shot):
            self.shot_info["points"][self.active_player] = 1

    def decide_winner(self, shot):
        self.winner = self.active_player

    def award_ball_in_hand(self, shot):
        self.shot_info["ball_in_hand"] = None

    def respot_balls(self, shot):
        pass

    def is_turn_over(self, shot):
        if not self.shot_info["is_legal"]:
            return True

        if is_hit(shot):
            return False

        return True

    def is_game_over(self, shot):
        for player in self.players:
            if player.points == self.points_to_win:
                return True
        return False

    def legality(self, shot):
        """Returns whether or not a shot is legal, and the reason"""
        return (True, None)

    def advance(self, shot):
        super().advance(shot)


def is_hit(shot, clean=False):
    # Which ball is in motion?
    for ball in shot.balls.values():
        if ball.history.s[0] in (c.rolling, c.sliding):
            cue = ball.id
            break
    else:
        raise ConfigError("three_cushion.is_hit :: no ball is in motion")

    get_other_agent = (
        lambda event: event.agents[0].id
        if event.agents[0].id != cue
        else event.agents[1].id
    )

    def get_agent_ids(event):
        return [agent.id for agent in event.agents]

    first_hit = False
    second_hit = False
    cushion_count = 0
    for event in shot.events:
        if event.event_type == "ball-cushion" and event.agents[0].id == cue:
            cushion_count += 1

        if not first_hit and event.event_type == "ball-ball":
            first_hit_agent = get_other_agent(event)
            first_hit = True
            continue

        if not second_hit and event.event_type == "ball-ball":
            agents = get_agent_ids(event)
            if cue not in agents:
                if clean:
                    return False
            elif get_other_agent(event) == first_hit_agent:
                if clean:
                    return False
            else:
                second_hit = True
                break
    else:
        return False

    if cushion_count < 3:
        return False

    return True


def which_hit_first(shot):
    # Which ball is in motion?
    for ball in shot.balls.values():
        if ball.history.s[0] in (c.rolling, c.sliding):
            cue = ball.id
            break
    else:
        raise ConfigError("three_cushion.is_hit :: no ball is in motion")

    get_other_agent = (
        lambda event: event.agents[0].id
        if event.agents[0].id != cue
        else event.agents[1].id
    )

    def get_agent_ids(event):
        return [agent.id for agent in event.agents]

    for event in shot.events:
        if event.event_type == "ball-ball":
            first_hit_agent = get_other_agent(event)
            break
    else:
        return False

    return first_hit_agent


def get_shot_components(shot):
    # Which ball is in motion?
    for ball in shot.balls.values():
        if ball.history.s[0] in (c.rolling, c.sliding):
            cue = ball.id
            break
    else:
        raise ConfigError("three_cushion.get_shot_components :: no ball is in motion")

    get_other_agent = (
        lambda event: event.agents[0].id
        if event.agents[0].id != cue
        else event.agents[1].id
    )

    def get_agent_ids(event):
        return [agent.id for agent in event.agents]

    first_hit, second_hit = False, False
    shot_components = []
    for event in shot.events:
        if event.event_type == "ball-cushion":
            ball, cushion = event.agents
            if ball.id != cue:
                continue
            shot_components.append(cushion.id)

        if not first_hit and event.event_type == "ball-ball":
            first_hit_agent = get_other_agent(event)
            shot_components.append(first_hit_agent)
            first_hit = True
            continue

        if not second_hit and event.event_type == "ball-ball":
            agents = get_agent_ids(event)
            if cue not in agents:
                continue
            elif get_other_agent(event) == first_hit_agent:
                continue
            else:
                shot_components.append(get_other_agent(event))
                second_hit = True
                break

    return tuple(shot_components)
