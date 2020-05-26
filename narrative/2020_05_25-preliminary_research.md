# Preliminary Research

I wanted to tackle the following questions before starting this journey:

1. What kind physics has been done on billiards?
2. How do state of the art pool simulators work?

So I did some research on both these topics...

## What kind physics has been done on billiards?

The thing about pool is that its pretty old. This piece of art, which please God let it be famous
for no other reason than it representing the first historical depiction of billiards, dates back to
1674.

<img src="media/1674.png" width="450" />
By Charles Cotton - Appearing in introductory history chapter (p.iv) of Joseph Bennett's 1894 book, Billiards (publisher T. de la Rue), as taken from Charles Cotton's 1674 book, The Compleat Gamester., Public Domain, https://commons.wikimedia.org/w/index.php?curid=6903484

Coincidentally, at exactly this point in history Isaac Newton would have been busy inventing
calculus, his self-titled Newtonian physics, and a universal theory of gravitation that wholly
explained the previously disparate phenomena of tides, why things fall, and the motions of celestial
bodies. His contributions to science would spark a revolution in the physical sciences more
illustrious than anyone before him, and arguably ever since him. But most importantly by far, Newton's
work would enable the theoretical treatment of the game of billiards, and as such, the game has been
studied for at least 200 years.

As a result of its long history, the theoretical treatment of billiards has been sufficiently solved
for most scenarios: the trajectories of the balls and their interaction with the cloth, the
collision of one ball with another, as well as with the cushion. The jury is still out on the finer
details of many of these interactions, and some treatments are less accurate than others (treatments
of ball-cushion interactions tend to make oversimplifying assumptions due to the compressible
geometry of cushions throughout the interaction), but each of these individual scenarios have
analytical solutions (no discrete time integration).

This is great, because I don't have to get my hands dirty in physics, something I was hoping to
avoid as much as possible. Nevertheless, as a reference source, I decided to pick up the
non-exhaustive but heavily referenced "modern day" treatment of billiards, "_The
Physics of Pocket Billiards_" by Wayland C. Marlow. Here is it's modest cover:

<img src="media/marlow.jpg" width="450" />

## How do state of the art pool simulators work?

The shining greats in terms of physics realism are without a doubt and ShootersPool Billiards
Simulation and Virtual Pool 4. Look at the pure beauty of this ShootersPool demo:

[![ShootersPool](http://img.youtube.com/vi/sDW0ENZzClk/0.jpg)](https://www.youtube.com/watch?v=sDW0ENZzClk "ShootersPool")

Both from a graphics and physics perspective, this appears very real. The only physical inaccuracy I
can spot is as balls are entering the pockets they seem to undergo a pre-baked animation rather than
interacting genuinely with the pocket. Here is the trailer for Virtual Pool 4:

[![Virtual Pool 4](http://img.youtube.com/vi/mAxACAt6m8g/0.jpg)](https://www.youtube.com/watch?v=mAxACAt6m8g "Virtual Pool 4")

Less impressive graphics and no slo-mo shots to scrutinize in careful detail, but having played the
game myself, I can attest to the quality of the physics.

So how do these pool simulators actually work? I have no idea, and that is understandably by design.
I wasn't able to gain any insight into how much money these companies are making from pool games but
let me know if you have any estimates. Regardless, both of these projects have been monetized and
have reason to keep their algorithms to themselves.

So the bottom line is that I have no idea what's going on under the hood in these games, but by
doing some research I think all pool simulators are going to fall under these two umbrellas:
discrete time integration, or continuous event-based integration. So let's talk about these.

## Pool simulator research

I never had any intention of developing this from scratch. To that end, I started researching
academical papers on pool simulation, which are surprisingly numerous. Usually, the research is
motivated by developing a realistic/fast physics engine as a necessary precursor to creating a robot
that can play pool:

[![Pool Robot](http://img.youtube.com/vi/4ArBw9kEMMw/0.jpg)](https://www.youtube.com/watch?v=4ArBw9kEMMw "Pool Robot")

Another application is to study game theory and make a billiards AI. In any case, during my literature
review I stumbled upon the work of Leckie and Greenspan entitled [An Event-Based Pool Physics
Simulator](https://link.springer.com/chapter/10.1007/11922155_19). A free pre-print of this
publication is available
[here](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.89.4627&rep=rep1&type=pdf). This is
a pretty groundbreaking paper, because they develop a method to solve the trajectories of pool balls
that avoid discrete time integration, the most common way to evolve many-body systems through time.
To contextualize their algorithm, I should first talk about what they avoid doing: time integration.

### Discrete Time Integration

Simply put, discrete time integration works by advancing the state forward in small time steps,
let's say an amount $dt$. At each timepoint $t$, the forces governing the motions are calculated,
and then all of the bodies' states (positions, velocities, etc.) are advanced to $t + dt$, under the
assumption that the forces are constant over that duration. It is critical that these time steps are
small enough, otherwise the evolution will be physically inaccurate. To see why, consider the example of
one ball hitting another:

Let's say the goal is to determine the collision time as accurately as possible. So Ball A on the
bottom is moving with a constant velocity towards Ball B. At each timestep, it is checked whether
the collision has occurred, which is done checking if the balls intersect. In the first panel a
large timestep is chosen, and we can see that the collision is detected well after the balls first
intersect. By choosing a smaller timestep like in the second panel we see a more accurate
determination of the time of collision.

So the smaller the time step, the more accurate this assumption is. But this comes at the cost of
subdividing your simulation time into smaller and smaller timesteps, each which come with increased
cost of computation. This can become brutal when dealing with pool simulations. Ball speeds commonly
reach $10$ m/s, and a reasonable requirement for realism is that 2 balls should never intersect more
than $1/100$th of a ball radius ($0.3$ mm). The required timestep for this level of realism is then
$30$ microseconds. If the time from the cue strike to the last ball rolling is 10 seconds, that is
$30,000$ time steps in total for one shot. If the level of realism is $1/1000$th a ball radius, that
is $300,000$ time steps. Yikes.

The problem with this is all of the wasted computation... I don't need $30$ microsecond time steps
when all of the balls are far apart and barley moving. It is only really in select scenarios, such a
pool break, that realism demands such miniscule time steps. So a smart numerical integration
scheme would be to cut down on the number of time steps by making them
[adaptive](https://en.wikipedia.org/wiki/Adaptive_step_size) depending on the state of the system.
There are an infinite number of ways you could develop heuristics for an adaptive time stepper, that
may be based on the distances between balls (if they are far apart, increase the time step), or
based on velocities (if they are moving fast, decrease the time step). I'm not even going to go
there because the possibilities are endless, although I am convinced that if Virtual Pool 4 or
ShootersPool are using discrete time integration, they are using adaptive time stepping.

### Continuous Event-based Simulation

Even with adaptive time stepping, there is going to be wasted computation. So ideally, you'd want to
avoid it altogether. In the example of the colliding balls, what if we could predict when the
collision happens by using knowledge of their positions and velocities? After all, it looks plainly
obvious that they are going to collide, so why waste our time advancing with so many time steps?
Let's add some variables to the picture and solve for $t$!

FIXME

$R$ is the ball radii, $v$ is the speed of the ball, and $d$ is the distance they are from collision
the collision state. If we assume that the Ball A moves with constant velocity, the time until
collision is quiter simply $\tau = d/v$.

This has some serious advantages over time integration. First, it is computationally much more
efficient. It was just one instance of arithmetic: $d/v$. Second, it is not subject to
discretization error. In the discrete time integration method above, the collision is detected
_after_ it happened since the collision is detected by seeing if the balls are intersecting. But if
they are intersecting, they already collided! This is what I'm calling discretization error. In
contrast, there is no error in $d/v$, save for floating point error.

This is actually a huge deal from the perspective of simulation, but it requires mathematical
formulas for the positions of the bodies as a function of time, and in most multi-body systems, this
is too much to ask. For example, the system of 3 planets exhibiting gravitational forces on one
another has no analytical mathematical formula for the positions as a function of time. Look at how
complex the solution becomes:

FIXME (embed and hyperlink goes to wiki)

<img src="media/3_body_problem.gif" width="450" />
By Dnttllthmmnm - Own work, CC BY-SA 4.0, https://commons.wikimedia.org/w/index.php?curid=59538221

#### The algorithm is essentially this

In the above case, discrete numerical integration is a necessity. So is a necessity for pool physics
too? Well, unlike the 3-body gravitational problem which exhibit forces on each other even at a
distance, balls only interact with each other during extremely brief collisions (OK fine, pool balls
also exhibit gravitational forces on each other at a distance, but you're just being pedantic).
Other than during these brief moments, the trajectories of the balls have closed-form equations that
describe their positions, velocities, and spins. So this doesn't solve the problem entirely, but I
can at least accurately simulate the evolution of a pool shot from $t=0$ up to the first collision
without any time integration because I have analytical forms of the trajectories as a function of
time! Then I could apply some well-trodden physics to resolve the
collision, and then evolve the state of all balls until the _next_ collision. Essentially, if you
can solve when a collision happens, you can evolve all balls up to that point in time, solve the
collision's physics by updating the states of the ball(s) involved in the collision, and then
advance time to the next collision. Rinse and repeat.

That's pretty good news, but it is still unknown how to calculate when the first collision occurs.
The solution employed by Leckie and Greenspan is to calculate all possible collision times and take
the one that occurs in the minimal amount of time. When I say all, I mean all.  Since the
trajectories of each ball are known as a function of time (they are quadratic with respect to time
because of the deceleration from the cloth), the collision time between each pair of balls can be
calculated from a fourth order polynomial with respect to time. The roots of this polynomial are the
time needed for the balls to collide. As we know, most balls will not collide--a typical shot will
have maybe 1 or 5 collisions.  The absence of a collision manifests mathematically as negative or
imaginary values to the roots of the fourth order polynomial. So if you have $15$ balls, that means
you have $105$ collision pairs to check, and most of these will not collide (yielding negative or
imaginary values). Yet a subset of these ball-pairs _will_ yield positive real values.  If a
ball-pair yields a non-negative real value, it means that if no other balls or cushions were to "get
in the way" of the collision, the balls would collide in a finite amount
of time. By picking the
one with a smallest postive and real-valued solution to the quartic polynomial, we ensure by
definition that this is the first collision that occurs.

With this time value in hand, we advance the trajectories of _all_ balls up to that point in time,
at which point a collision is occuring, i.e. 2 balls or a ball and a rail are touching. Then, we
apply well-trodden physics that explains the outgoing states of the balls as a result of the
collision (which we assume is instantaneous). After updating the states of the involved balls, we
rinse and repeat: We find the next event, advance the states of all balls up to that time by using
the analytical expressions we have, resolve the physics of the collision, and so on and so forth.

Here is my sketch of the algorithm:

FIXME

## Continuous Event-based simulation is da way man

After doing my resarch, I realized I have _got_ to do a continuous event-based approach. Leckie and
Greenspan give a very rough complexity analysis as to why this is far superior to discrete numerical
integration. For discrete numerical integration, the number of operations is on the order of 

$N (61 n - n^2) / 2$

where $n$ is the number of balls, and $N$ is the number of time steps. OK well writing this down
now, I see this is clearly quite a garbage expression because the number of operations grows
negative with large values of $n$. But the important part is this: time complexity scales linearly
with the number of time steps, i.e. accuracy. But assuming it works for small values of $n$, simulating 3 balls
for 1 second using a very coarse time step of 1 millisecond yields $87,000$ required computations.
In contrast, their derived time complexity expression for their continuous event-based approach is

$(645 n - 19 n^2) / 2$

Which yields only 882 operations. More critically, the complexity depends _only_ on the number of
balls.

The bottomline is this: after reading this paper, I decided this project was going to offer
continuous event-based simulations or it wasn't going to offer anything.
