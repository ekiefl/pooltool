# Physics

This is the physics package of pooltool.

## Units

A convention is upheld for the input and output variable names that is
consistent across functions. All units are SI
(https://en.wikipedia.org/wiki/International_System_of_Units)

## Variable names

- `rvw`: The ball state (https://ekiefl.github.io/2020/12/20/pooltool-alg/#what-is-the-system-state). It is a 3x3 numpy array where rvw[0, :] is the displacement vector (r), rvw[1, :] is the velocity vector (v), and rvw[2, :] is the angular velocity vector (w). For example, rvw[1, 1] refers to the y-component of the velocity vector.

- `R`: The radius of the ball.

- `m`: The mass of the ball.

- `h`: The height of the cushion.

- `s`: The motion state of the ball. Definitions are found in pooltool.state_dict

- `mu`: The coefficient of friction. If ball motion state is sliding, assume coefficient of sliding friction. If rolling, assume coefficient of rolling friction. If spinning, assume coefficient of spinning friction

- `u_s`: The sliding coefficient of friction.

- `u_sp`: The spinning coefficient of friction.

- `u_r`: The rolling coefficient of friction.

- `e_c`: The cushion coefficient of restitution

- `f_c`: The cushion coefficient of friction

- `g`: The acceleration due to gravity felt by a ball.
