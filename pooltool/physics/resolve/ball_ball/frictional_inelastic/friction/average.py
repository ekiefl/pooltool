from pooltool.objects.ball.datatypes import Ball


class AverageBallBallFriction:
    def calculate_friction(self, ball1: Ball, ball2: Ball) -> float:
        return (ball1.params.u_b + ball2.params.u_b) / 2
