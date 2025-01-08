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

#### Create a name for your model

Figure out a name for your model, then open up `pooltool/physics/resolve/models.py`. You'll see a bunch of [Enum](https://docs.python.org/3/howto/enum.html) classes. Find the one corresponding to your event class and add your model as an attribute of the class.

Here's the example code: [d7ab8531424b62e1786506245b46715a607305ee](https://github.com/ekiefl/pooltool/commit/d7ab8531424b62e1786506245b46715a607305ee)

#### Create a directory

Now, we need to establish the model within its own dedicated directory. This directory should be named after the model. The directory should be located in one of the `pooltool/physics/resolve/*` folders, depending on the event class your model manages. Since I'm constructing a ball-cushion model, I'll create the `unrealistic` folder in `pooltool/physics/resolve/ball_cushion/`.

Within your model directory, create an `__init__.py` file. If your model is simple, all your model logic can be contained within this single file. However, if your model grows complex, feel free to expand it across multiple files, provided they're kept within your model directory.

Here's the example code: [7ded13254150cdebb09013fa35e6fe0846d59ea9](https://github.com/ekiefl/pooltool/commit/7ded13254150cdebb09013fa35e6fe0846d59ea9)

#### Create the template

Regardless of how you choose to structure your code, it must eventually lead to a class that:

1. Contains a method named `solve`.
1. Inherits from the core model.

There's two other requirements but let's deal with these two first.

The call signature of your `solve` method and the core model from which you inherit will depend on the event class you're developing a model for.

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

With these, we can draft our template by following the example code: [5ecddb2c0c010e3f058e666fd5a7fc1f10117638](https://github.com/ekiefl/pooltool/commit/5ecddb2c0c010e3f058e666fd5a7fc1f10117638)

It's just missing two things. First, the class must be an attrs class[^attrs]. Second, the class must have an attribute called `model`, and this attribute should be the Enum member that you had previously added to `pooltool/physics/resolve/models.py`.

[^attrs]: Pooltool requires that all the resolver models are [attrs](https://www.attrs.org/en/stable/) classes. If you've never used attrs before, stick close to the example and you'll have no problems.

To apply these changes, follow the example code: [9c12a6efa2b9d201d8cedfc75b1a83b8134dd7ec](https://github.com/ekiefl/pooltool/commit/9c12a6efa2b9d201d8cedfc75b1a83b8134dd7ec). Since I added `UNREALISTIC` to the `BallLCushionModel` model, I added the following attribute to my class:

```python
model: BallLCushionModel = attrs.field(default=BallLCushionModel.UNREALISTIC, init=False, repr=False)
```

Great, now we are done with the boilerplate code. But `resolve` currently does *nothing*, it just returns what is handed to it. Let's change that.

#### Implement the logic

:::{note}
You may prefer **registering** and **activating** your model before you start implementing the logic. Even though your model doesn't do anything at this point, you may prefer registering and activating it now, so that you can make changes, and immediately see how your implementation affects a test case.
:::

This is where you come in, but there are a few points to make. First, I really like type hints, but I remember a time when I didn't. If that's you, don't worry about them--or any other conventions I follow, for that matter. This is your code, just do your thing and don't get overwhelmed in my conventions.

Second, since you'll be working with the core pooltool objects `Cue`, `Ball`, `LinearCushionSegment`, `CircularCushionSegment`, and `Pocket`, it is worth scanning their source code to determine what parameters they have, and therefore what tools you have at your disposal.

Anyways, here's my preliminary implementation: [f5cf3734a026508c8767e8937b5dccb4e3a87682](https://github.com/ekiefl/pooltool/commit/f5cf3734a026508c8767e8937b5dccb4e3a87682)

Then I added a parameter to the model to add some complexity. Specifically, here's how I added a model parameter that dictates whether or not the outgoing speed should be dampened with the ball's restitution coefficient: [3c898c72832421aa6226cd40574a1b9b38550737](https://github.com/ekiefl/pooltool/commit/3c898c72832421aa6226cd40574a1b9b38550737).

:::{note}
Model parameters should not be things like mass or friction coefficients. Those are properties of the passed objects. If you think a property is missing for an object, we can add it to the object. Model parameters are more meta/behavioral (see the above commit, where `restitution` is added).
:::

:::{note}
Attributes are defined differently for attrs classes than they are for standard Python classes. For example, if you had a standard class, you could add a restitution boolean like this:

```python
class UnrealisticLinear(CoreBallLCushionCollision):
    def __init__(self, restitution: bool = True):
        self.restitution = restitution
```

But since pooltool uses attrs classes for model definitions, you must define the equivalent like this:

```python
@attrs.define
class UnrealisticLinear(CoreBallLCushionCollision):
    restitution: bool = True
```

Keep this in mind if you are adding parameters to your model.
:::

#### Register the model

Your model is in the codebase, but it needs to be added to collection of *available* models. Changing that is simple.

Open the `__init__.py` file corresponding to your event class:

```
pooltool/physics/resolve/ball_ball/__init__.py
pooltool/physics/resolve/ball_cushion/__init__.py
pooltool/physics/resolve/ball_pocket/__init__.py
pooltool/physics/resolve/stick_ball/__init__.py
pooltool/physics/resolve/transition/__init__.py
```

In it you'll find a variable that defines the model registry for your event class. Since I'm adding a ball linear cushion model, I opened up `pooltool/physics/resolve/ball_cushion/__init__.py` where I found the model registry `_ball_lcushion_model_registry` that looked like this:

```python
_ball_lcushion_model_registry: Tuple[Type[BallLCushionCollisionStrategy], ...] = (
    Han2005Linear,
)
```

Now add your model. My model is called `UnrealisticLinear`, so I added it to the registry:

```python
_ball_lcushion_model_registry: Tuple[Type[BallLCushionCollisionStrategy], ...] = (
    Han2005Linear,
    UnrealisticLinear,
)
```

I needed to import my new model, so I put this at the top of the file:

```python
from pooltool.physics.resolve.ball_cushion.unrealistic import UnrealisticLinear
```

Here are the full changes: [bb787a43d276d1b4f887c52e7bc5b5b1d079efd7](https://github.com/ekiefl/pooltool/commit/bb787a43d276d1b4f887c52e7bc5b5b1d079efd7)

#### Activate the model

In order to apply your new model using pooltool, you'll need to modify the default resolver file (`~/.config/pooltool/physics/resolver.yaml`). This file is automatically generated **upon the first run-time**. Therefore, if it's missing, simply execute the command `python sandbox/break.py` from the pooltool root directory to generate it.

Next, you need to replace the existing model name with the name of your new model. My default entry for the linear cushion model looked like this:

```
ball_linear_cushion:
  model: han_2005
```

So I replaced it with my model:

```
ball_linear_cushion:
  restitution: true
  model: unrealistic
```

It's important to note that the model value should be the **lower case version of the Enum attribute**. For instance, my Enum attribute is `UNREALISTIC`, so I put `unrealistic`. Since my model accepts the parameter `restitution`, I also supply a value for that parameter.

That's it. If everything runs without error, your model is active.

Note, there is no git commit to show you here, because `~/.config/pooltool/physics/resolver.yaml` isn't part of the project--it's part of your personal workspace.

#### Addendum: ball-cushion models

These are instructions for taking your ball-linear cushion model and creating a corresponding ball-circular cushion model.

The ball-cushion collision has two event classes: collision of the ball with (1) linear cushion segments and (2) circular cushion segments. Circular cushion segments exist to smoothly join two linear cushion segments, _e.g._ to create the jaws of a pocket.

You could have separate models for circular and linear cushion segment collisions, or if you're lazy they could mimic each other. In this git commit, I illustrate how you can use the same model for both collision types, assuming you've already implemented the linear cushion segment: [e99b77d73ddbd6979bfa24797f8dfca25dd1cbe8](https://github.com/ekiefl/pooltool/commit/e99b77d73ddbd6979bfa24797f8dfca25dd1cbe8)

If you want to activate the model, don't forget to activate it in `~/.config/pooltool/physics/resolver.yaml`.
