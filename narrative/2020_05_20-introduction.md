# Introduction

## Disclaimer

I'm going to talk about pool, physics, math, softare, video game design, 3D modelling, and a bunch
of things that this project has led me to. But I am not pro pool player, physicist, mathematician,
software developer, video game designer, Blender guru, or anything. So much of what I say may be
misinformative, or even rub experts the wrong way. My apologies in advance for when such instances
inevitably arise.

## Motivation

Seven years ago (2013) I was an in undergraduate math class called "_Non-linear Dynamical Systems and
Chaos_" taught by Dr. Anthony Quas at the Univerity of Victoria. Our final project was to investigate
a chaotic system. Adam Paul, a good friend of mine, and I decided we would work on the same project.
Since we would regularly ditch working on class assignments to instead play pool at the on-campus
pub, it seemed natural to pick pool as our chaotic system.
[Chaos](https://en.wikipedia.org/wiki/Chaos_theory) is loosely speaking defined
as a deterministic (non-random) system that exhibits extreme sensitivity to initial conditions, and so we
figured the pool break perfectly fit this description: the balls are governed by non-random and some
would argue even simplistic Newtonian physics, yet each break outcome appears unique and
irreproducible (unless you're Shane Van Boening). Ignoring variability in the cue ball velocity,
this implies that the vastness of break outcomes are determined by the milli- or maybe even
micro-meter pertubations in ball spacings in a given rack. To study this, we decided would create a
physics simulation in Python that simulated the break.

It kind of sounds like I'm chalking us up to having accomplished something amazing, however I would
like to assure you our accomplishments were far from impressive. From a physics standpoint, our model was very
skeletal. Every collision was instantaneous and elastic, and the trajectories were restricted to 2D.
We applied conservation of momentum and energy, and voila, that was our physics. From an
implementation standpoint, we used a discrete time integration approach with a constant time step, which is
computationally very ineffecient. Algorithm aside, the program exhibits zero respect for the art of programming
and is so poorly implemented with hardcoded variables and spaghetti logic that no one in their right
mind should lay eyes on it. I think showing the product of our efforts is in order:

<img src="media/2013_project.gif" width="450" />

Not exactly what you would call realistic, or pretty. The GIF has a shitty black bar on the
bottom, which I find deserving. The [quality of the code](media/2013_project.py) is even worse than
the animation.

Because of the drastic potential for improvement, this project kind of sat in the back of my head for years as
unfinished business. Time passed, I got more invested in pool, bought my own table, joined a pool
league. Concurrently, I started a PhD at the University of Chicago doing computational biology, and
developed considerably as a programmer due to my line of research. Then the COVID-19 pandemic
struck and I realized I needed something other than work to keep me stimulated during quarantine.
That's when I decided to undertake this project.

## Goal

With all that said, the goal of this project is to make as realistic a pool physics engine as
possible. Much the way that this is a stream of consciousness blog, in a way this is also a stream
of consciousness project. I don't always know where its going. At first, it was to make an open
source python physics engine, and at the time of writing this it is to make a pool physics
exploration tool with 3D graphics--not quite a game, but kind of a game. I also want to write an AI
pool player that uses the engine. Who knows. No guarantees. This isn't a good way to setup your
expectations, proceed at your own risk.
