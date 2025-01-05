:::{note}
**This is under construction (work in progress)!**
:::

# Modular Physics

One of pooltool's founding ambitions is completely customizable physics.

Loosely speaking, the physics in pooltool can be simplified into two categories:

1. **Evolution** - refers to the physics that governs ball trajectories over time in the absence of interupting collisions.
2. **Resolution** - refers to the physics that resolves the outcome of a collision, _e.g._ a ball-ball collision or ball-cushion collision.

## Evolution

Unfortunately, **evolution** physics are not yet modular. That means the ball trajectories are governed by the equations presented in [this blog](https://ekiefl.github.io/2020/04/24/pooltool-theory/#3-ball-with-arbitrary-spin) and no other equations can be easily substituted in without overwriting these equations in the source code.

**The equations can still be modified by changing parameters governing the trajectories**, like ball mass, radius, and coefficients of friction, but no matter how you change these parameters, it's still the same underlying model.

## Resolution

Pooltool supports modular physics for resolving events. To clarify, [events](https://ekiefl.github.io/2020/12/20/pooltool-alg/#2-what-are-events) refer to either collisions or transitions. The way in which an event is resolved depends on the strategy you choose to employ.

Below details how you can either **(a)** plug in models that already exist in the codebase and **(b)** write your own custom models.

### Modify

This section guides you on how to switch between existing models within the codebase.

By default, events are resolved according to the default resolver file, which is located at `~/.config/pooltool/physics/resolver.yaml`. Here's an example of what that looks like:

```yaml
ball_ball:
  friction:
    a: 0.009951
    b: 0.108
    c: 1.088
    model: alciatore
  num_iterations: 1000
  model: frictional_mathavan
ball_linear_cushion:
  model: han_2005
ball_circular_cushion:
  model: han_2005
ball_pocket:
  model: canonical
stick_ball:
  english_throttle: 1.0
  squirt_throttle: 1.0
  model: instantaneous_point
transition:
  model: canonical
version: 6
```

:::{note}
The resolver configuration file is automatically generated during the initial execution. If you don't have one yet, execute pooltool with the command `run-pooltool`, start a new game, and take a shot--one will be generated.
:::

You can modify this file to change the physics. You can view available model names and their associated parameter values by executing the following command:

```python
python -c 'from pooltool.physics.resolve import display_models; display_models()'
```

Here is the output (January 5th, 2025):

```
ball_ball models:
  frictionless_elastic (/Users/evan/Software/pooltool_ml/pooltool/pooltool/physics/resolve/ball_ball/frictionless_elastic/__init__.py)
  frictional_inelastic (/Users/evan/Software/pooltool_ml/pooltool/pooltool/physics/resolve/ball_ball/frictional_inelastic/__init__.py)
      - friction: type=<class 'pooltool.physics.resolve.ball_ball.friction.BallBallFrictionStrategy'>, default=AlciatoreBallBallFriction(a=0.009951, b=0.108, c=1.088)
  frictional_mathavan (/Users/evan/Software/pooltool_ml/pooltool/pooltool/physics/resolve/ball_ball/frictional_mathavan/__init__.py)
      - friction: type=<class 'pooltool.physics.resolve.ball_ball.friction.BallBallFrictionStrategy'>, default=AlciatoreBallBallFriction(a=0.009951, b=0.108, c=1.088)
      - num_iterations: type=<class 'int'>, default=1000

ball_linear_cushion models:
  han_2005 (/Users/evan/Software/pooltool_ml/pooltool/pooltool/physics/resolve/ball_cushion/han_2005/model.py)
  unrealistic (/Users/evan/Software/pooltool_ml/pooltool/pooltool/physics/resolve/ball_cushion/unrealistic/__init__.py)
      - restitution: type=<class 'bool'>, default=True

ball_circular_cushion models:
  han_2005 (/Users/evan/Software/pooltool_ml/pooltool/pooltool/physics/resolve/ball_cushion/han_2005/model.py)
  unrealistic (/Users/evan/Software/pooltool_ml/pooltool/pooltool/physics/resolve/ball_cushion/unrealistic/__init__.py)
      - restitution: type=<class 'bool'>, default=True

stick_ball models:
  instantaneous_point (/Users/evan/Software/pooltool_ml/pooltool/pooltool/physics/resolve/stick_ball/instantaneous_point/__init__.py)
      - english_throttle: type=<class 'float'>, default=1.0
      - squirt_throttle: type=<class 'float'>, default=1.0

ball_pocket models:
  canonical (/Users/evan/Software/pooltool_ml/pooltool/pooltool/physics/resolve/ball_pocket/__init__.py)

ball_transition models:
  canonical (/Users/evan/Software/pooltool_ml/pooltool/pooltool/physics/resolve/transition/__init__.py)
```

Next to each model name is the filepath where the model is defined. For example, the **stick-ball** collision model `instantaneous_point` is defined at `pooltool/physics/resolve/stick_ball/instantaneous_point/__init__.py`. As you can see in the output above, it has two parameters, `english_throttle` and `squirt_throttle`. If you look at the corresponding class `InstantaneousPoint` housed in that file, you can see that these are initialization parameters of the model:

```python
@attrs.define
class InstantaneousPoint(CoreStickBallCollision):
    english_throttle: bool
    squirt_throttle: bool

    def solve(self, cue: Cue, ball: Ball) -> Tuple[Cue, Ball]:
        (...)
```

### What happens at runtime?

This may be a useful section for you if you want to learn more about how this all works.

#### `Resolver`

The cornerstone of event resolution is [](#pooltool.physics.resolve.resolver.Resolver). An instance of `Resolver` is either passed to or generated by the shot evolution algorithm, and it is this instance that exclusively determines how events are resolved.

This is the structure of `Resolver`:

```python
class Resolver:
    ball_ball: BallBallCollisionStrategy
    ball_linear_cushion: BallLCushionCollisionStrategy
    ball_circular_cushion: BallCCushionCollisionStrategy
    ball_pocket: BallPocketStrategy
    stick_ball: StickBallCollisionStrategy
    transition: BallTransitionStrategy
```

Each attribute is a _physics strategy_ (or model) for each event class: [ball-ball collisions](https://ekiefl.github.io/2020/12/20/pooltool-alg/#ball-ball-collision), [ball-linear cushion collisions](https://ekiefl.github.io/2020/12/20/pooltool-alg/#ball-cushion-collision), [ball-circular cushion collisions](https://ekiefl.github.io/2020/12/20/pooltool-alg/#ball-cushion-collision), [ball-pocket "collisions"](https://ekiefl.github.io/2020/12/20/pooltool-alg/#ball-pocket-collision), and [ball motion transitions](https://ekiefl.github.io/2020/12/20/pooltool-alg/#transition-events).

You might observe that this closely resembles the YAML configuration file. That's because the `resolver.yaml` file is simply a serialization of this class. During runtime, a `Resolver` class is created from the `resolver.yaml`.

### Creating new physics models

To demonstrate how you can integrate your own physics model into pooltool, I'll be incorporating a mock ball-cushion model suitable for both linear and circular segments. I'll outline the general steps here, and for each step, I'll include a link to a commit where you can view the specific files I modified. By following these patterns, the process should be quite straightforward.

Ok let's get started.

#### Create a directory

First, we need to establish a model within its own dedicated directory. This directory should be named after the model. As I'm using a simple toy example, I'll name mine `unrealistic`. The directory should be located in one of the `pooltool/physics/resolve/*` folders, depending on the event class your model manages. Since I'm constructing a ball-cushion model, I'll create the `unrealistic` folder in `pooltool/physics/resolve/ball_cushion/`.

Within your model directory, create an `__init__.py` file. If your model is simple, all your model logic can be contained within this single file. However, if your model grows complex, feel free to expand it across multiple files, provided they're kept within your model directory.

Here's the example code: [7ded13254150cdebb09013fa35e6fe0846d59ea9](https://github.com/ekiefl/pooltool/commit/7ded13254150cdebb09013fa35e6fe0846d59ea9)

#### Create the template

Regardless of how you choose to structure your code, it must eventually lead to a class that:

1. Contains a method named `solve`.
1. Inherits from the core model.

The call signature of your `solve` method and the core model from which you inherit will depend on the event class for which you're developing a model.

Since I'm developing a ball-cushion model, I'll refer to `pooltool/physics/resolve/ball_cushion/core.py` for this information. Below is the required call signature for my `solve` method:

```python
class BallLCushionCollisionStrategy(_BaseLinearStrategy, Protocol):
    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> Tuple[Ball, LinearCushionSegment]:
        ...
```

It takes a ball and linear cushion, and then returns a ball and linear cushion. Simple enough.

And here is the required core model:

```python
class CoreBallLCushionCollision(ABC):
    """Operations used by every ball-linear cushion collision resolver"""
    (...)
```

With these, we can create our template:

```python
"""An unrealistic ball-cushion model"""

from typing import Tuple

from pooltool.objects.ball.datatypes import Ball
from pooltool.objects.table.components import LinearCushionSegment
from pooltool.physics.resolve.ball_cushion.core import CoreBallLCushionCollision


class UnrealisticLinear(CoreBallLCushionCollision):
    def solve(
        self, ball: Ball, cushion: LinearCushionSegment
    ) -> Tuple[Ball, LinearCushionSegment]:
        return ball, cushion
```

Here's the example code: [af507032217914629e53954965c982d21fdc8094](https://github.com/ekiefl/pooltool/commit/af507032217914629e53954965c982d21fdc8094)

As you can see, `resolve` currently does *nothing*, it just returns what is handed to it.

#### Implement the logic

:::{note}
You may prefer **registering** and **activating** your model before you start implementing the logic. Even though your model doesn't do anything at this point, you may prefer registering and activating it now, so that you can make changes, and immediately see how your implementation affects a test case.
:::

This is where you come in, but there are a few points to make. First, I really like type hints, but I remember a time when I didn't. If that's you, don't worry about them--or any other conventions I follow, for that matter. This is your code, just do your thing and don't get overwhelmed in my conventions.

Second, since you'll be working with the core pooltool objects `Cue`, `Ball`, `LinearCushionSegment`, `CircularCushionSegment`, and `Pocket`, it is worth scanning their source code to determine what parameters they have, and therefore what tools you have at your disposal.

Anyways, here's my preliminary implementation: [17510e7d014c8aa5e60d6556db2e5b0dea36f2f0](https://github.com/ekiefl/pooltool/commit/17510e7d014c8aa5e60d6556db2e5b0dea36f2f0)

Then I added a parameter to the model to add some flavor and complexity. Note that the model parameters should not be things like mass or friction coefficients. Those are properties of the passed objects. If you think a property is missing for an object, we can add it to the object. Model parameters are more meta/behavioral (see the below example).

Please note that the resolver config can only handle strings, booleans, floats, and integers for model parameters due to serialization requirements. If you have more complex model types like functions, try and simplify the passed argument to a string by string-lookup dictionary.

Here's me adding a model parameter that dictates whether or not the outgoing speed should be dampened with the ball's restitution coefficient: [ec42752f381edf3d576a66a9178a27d6054ff437](https://github.com/ekiefl/pooltool/commit/ec42752f381edf3d576a66a9178a27d6054ff437)

#### Register the model

Your model is in the codebase, but no other part of the codebase knows about it yet. Changing that is simple.

Open the `__init__.py` file corresponding to your event class:

```
pooltool/physics/resolve/ball_ball/__init__.py
pooltool/physics/resolve/ball_cushion/__init__.py
pooltool/physics/resolve/ball_pocket/__init__.py
pooltool/physics/resolve/stick_ball/__init__.py
pooltool/physics/resolve/transition/__init__.py
```

You'll need to modify two objects.

First, is an [Enum](https://docs.python.org/3/library/enum.html) that holds the collection of all model names for a given event-class. You can find it by searching for a class that inherits from `StrEnum`. Here is the ball linear cushion Enum:

```python
class BallLCushionModel(StrEnum):
    HAN_2005 = auto()
```

Add a new element to this Enum that will correspond to your model, like I've done here:

```python
class BallLCushionModel(StrEnum):
    HAN_2005 = auto()
    UNREALISTIC = auto()
```

Technically the name here is arbitrary, but it makes good sense to have it match your model name.

Second, you'll have to modify a dictionary that associates model names to model classes. It's in the same file. Mine was this:

```python
_ball_lcushion_models: Dict[BallLCushionModel, Type[BallLCushionCollisionStrategy]] = {
    BallLCushionModel.HAN_2005: Han2005Linear,
}
```

And I made it this:

```python
_ball_lcushion_models: Dict[BallLCushionModel, Type[BallLCushionCollisionStrategy]] = {
    BallLCushionModel.HAN_2005: Han2005Linear,
    BallLCushionModel.UNREALISTIC: UnrealisticLinear,
}
```

I needed to import my new model, so I put this at the top of the file:

```python
from pooltool.physics.resolve.ball_cushion.unrealistic import UnrealisticLinear
```

Here are the full changes: [9c4d9ad2dc6bae3848bfc9973f150b864e07db06](https://github.com/ekiefl/pooltool/commit/9c4d9ad2dc6bae3848bfc9973f150b864e07db06)

#### Activate the model

In order to apply your new model using pooltool, you'll need to modify the resolver configuration file, which is found at `~/.config/pooltool/physics/resolver.yaml`. This file is automatically generated **upon the first run-time**. Therefore, if it's missing, simply execute the command `python sandbox/break.py` from the pooltool root directory to generate it.

Next, you need to replace the existing model name with the name of your new model. It's important to note that the model name should be the **lower case version of the Enum attribute**. For instance, if my Enum attribute is `UNREALISTIC`, I would input `unrealistic` for `ball_linear_cushion`.

If your model doesn't require parameters, you should set the `_params` key to `{}`. However, if your model does have parameters, you should list them, along with their corresponding values. For example, if my model includes a parameter, I would specify its value as follows:

```
ball_linear_cushion: unrealistic
ball_linear_cushion_params:
  restitution: true
```

That's it. If everything runs without error, your model is active.

Note, there is no git commit to show you here, because `~/.config/pooltool/physics/resolver.yaml` isn't part of the project--it's part of your personal workspace.

#### Addendum: ball-cushion models

This is instructions for taking your ball-linear cushion model and creating a corresponding ball-circular cushion model.

The ball-cushion collision has two event classes: collision of the ball with (1) linear cushion segments and (2) circular cushion segments. I developed circular cushion segments to smoothly join two linear cushion segments, _e.g._ to create the jaws of a pocket.


You could have separate models for circular and linear cushion segment collisions, or if you're lazy they could mimic each other. In this git commit, I illustrate how you can use the same model for both collision types, assuming you've already implemented the linear cushion segment: [f4b91e436976fb857bf7681fcb6458c3ae1e6377](https://github.com/ekiefl/pooltool/commit/f4b91e436976fb857bf7681fcb6458c3ae1e6377)

If you want to activate the model, don't forget to modify the resolver config.
