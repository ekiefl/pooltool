MODULE collisions
  USE iso_c_binding, only: c_double
  IMPLICIT NONE
  real(c_double), bind(C, name="M") :: M = 0.1406
  real(c_double), bind(C, name="R") :: R = 0.02625
  real(c_double), bind(C) :: mu_s = 0.21
  real(c_double), bind(C) :: mu_b = 0.05
  real(c_double), bind(C) :: e = 0.89
  double precision, dimension(3), parameter :: z_loc = (/ 0.d0, 1.d0, 0.d0 /)
  ! real(c_double), parameter :: ZERO_VELOCITY_CLIP = 0.0001
  ! real(c_double), parameter :: ZERO_VELOCITY_CLIP_SQRD = 0.00000001
  ! real(c_double), parameter :: ZERO_ANGULAR_VELOCITY_CLIP = 0.00001
  real(c_double), parameter :: grav = 9.81

CONTAINS

  SUBROUTINE collide_balls (deltaP,            &
                            r_i, v_i, omega_i, &
                            r_j, v_j, omega_j, &
                            v_i1, omega_i1, v_j1, omega_j1) BIND(C)
    implicit none
    double precision, VALUE, intent(in) :: deltaP
    double precision, dimension(3), intent(in) :: r_i, v_i, omega_i
    double precision, dimension(3), intent(in) :: r_j, v_j, omega_j
    double precision, dimension(3), intent(out) :: v_i1, omega_i1
    double precision, dimension(3), intent(out) :: v_j1, omega_j1
    double precision, dimension(3,3) :: G, G_T
    double precision, dimension(3) :: r_ij, deltaOm_i, deltaOm_j, y_loc, x_loc
    double precision :: v_ix, v_iy, v_jx, v_jy
    double precision :: omega_ix, omega_iy, omega_iz, omega_jx, omega_jy, omega_jz
    double precision :: u_iR_x, u_iR_y, u_jR_x, u_jR_y, u_iR_xy_mag, u_jR_xy_mag
    double precision :: u_ijC_x, u_ijC_z, u_ijC_xz_mag, v_ijy, v_ijy0
    double precision :: deltaP_ix, deltaP_iy, deltaP_jx, deltaP_jy, deltaP_1, deltaP_2
    double precision :: deltaV_ix, deltaV_iy, deltaV_jx, deltaV_jy
    double precision :: W, deltaW, W_f, W_c
    real(c_double), dimension(3) :: u
    real(c_double), dimension(3,3) :: a_i1, a_j1
    r_ij = r_j - r_i
    y_loc = r_ij / (2*R)
    x_loc(1) = -y_loc(3)
    x_loc(2) = 0
    x_loc(3) = y_loc(1)
    G(1,1:3) = x_loc
    G(2,1:3) = y_loc
    G(3,1:3) = z_loc
    G_T = transpose(G)
    v_ix = dot_product(v_i, x_loc)
    v_iy = dot_product(v_i, y_loc)
    v_jx = dot_product(v_j, x_loc)
    v_jy = dot_product(v_j, y_loc)
    omega_ix = dot_product(omega_i, x_loc)
    omega_iy = dot_product(omega_i, y_loc)
    omega_iz = dot_product(omega_i, z_loc)
    omega_jx = dot_product(omega_j, x_loc)
    omega_jy = dot_product(omega_j, y_loc)
    omega_jz = dot_product(omega_j, z_loc)
    u_iR_x = v_ix + R*omega_iy
    u_iR_y = v_iy - R*omega_ix
    u_jR_x = v_jx + R*omega_jy
    u_jR_y = v_jy - R*omega_jx
    u_iR_xy_mag = sqrt(u_iR_x**2 + u_iR_y**2)
    u_jR_xy_mag = sqrt(u_jR_x**2 + u_jR_y**2)
    u_ijC_x = v_ix - v_jx - R*(omega_iz + omega_jz)
    u_ijC_z =               R*(omega_ix + omega_jx)
    u_ijC_xz_mag = sqrt(u_ijC_x**2 + u_ijC_z**2)
    v_ijy = v_jy - v_iy
    ! omega_i1 = (/ omega_ix, omega_iy, omega_iz /)
    ! omega_j1 = (/ omega_jx, omega_jy, omega_jz /)
    omega_i1 = matmul(G, omega_i)
    omega_j1 = matmul(G, omega_j)
    W = 0
    W_f = huge(1.d0)
    W_c = huge(1.d0)
    do while (W < W_c .or. W < W_f)
       ! determine impulse deltas:
       if (u_ijC_xz_mag == 0) then
          deltaP_1 = 0
          deltaP_2 = 0
          deltaP_ix = 0
          deltaP_iy = 0
          deltaP_jx = 0
          deltaP_jy = 0
       else
          deltaP_1 = -mu_b * deltaP * u_ijC_x / u_ijC_xz_mag
          if (abs(u_ijC_z) == 0) then
             deltaP_2 = 0
             deltaP_ix = 0
             deltaP_iy = 0
             deltaP_jx = 0
             deltaP_jy = 0
          else
             deltaP_2 = -mu_b * deltaP * u_ijC_z / u_ijC_xz_mag
             if (deltaP_2 > 0) then
                deltaP_ix = 0
                deltaP_iy = 0
                if (u_jR_xy_mag == 0) then
                   deltaP_jx = 0
                   deltaP_jy = 0
                else
                   deltaP_jx = -mu_s * (u_jR_x / u_jR_xy_mag) * deltaP_2
                   deltaP_jy = -mu_s * (u_jR_y / u_jR_xy_mag) * deltaP_2
                endif
             else
                deltaP_jx = 0
                deltaP_jy = 0
                if (u_iR_xy_mag == 0) then
                   deltaP_ix = 0
                   deltaP_iy = 0
                else
                   deltaP_ix = mu_s * (u_iR_x / u_iR_xy_mag) * deltaP_2
                   deltaP_iy = mu_s * (u_iR_y / u_iR_xy_mag) * deltaP_2
                end if
             end if
          end if
       endif
       ! update velocities / angular velocities:
       v_ix = v_ix + ( deltaP_1 + deltaP_ix) / M
       v_iy = v_iy + (-deltaP   + deltaP_iy) / M
       v_jx = v_jx + (-deltaP_1 + deltaP_jx) / M
       v_jy = v_jy + ( deltaP   + deltaP_jy) / M
       deltaOm_i = 5.d0/(2*M*R) * (/ ( deltaP_2 + deltaP_iy), &
                                     (-deltaP_ix),            &
                                     (-deltaP_1) /)
       deltaOm_j = 5.d0/(2*M*R) * (/ ( deltaP_2 + deltaP_jy), &
                                     (-deltaP_jx),            &
                                     (-deltaP_1) /)
       omega_i1 = omega_i1 + deltaOm_i
       omega_j1 = omega_j1 + deltaOm_j
       omega_ix = omega_i1(1)
       omega_iy = omega_i1(2)
       omega_iz = omega_i1(3)
       omega_jx = omega_j1(1)
       omega_jy = omega_j1(2)
       omega_jz = omega_j1(3)
       ! update ball-table slips:
       u_iR_x = v_ix + R*omega_i1(2)
       u_iR_y = v_iy - R*omega_i1(1)
       u_jR_x = v_jx + R*omega_j1(2)
       u_jR_y = v_jy - R*omega_j1(1)
       u_iR_xy_mag = sqrt(u_iR_x**2 + u_iR_y**2)
       u_jR_xy_mag = sqrt(u_jR_x**2 + u_jR_y**2)
       ! update ball-ball slip:
       u_ijC_x = v_ix - v_jx - R*(omega_i1(3) + omega_j1(3))
       u_ijC_z = R*(omega_i1(1) + omega_j1(1))
       u_ijC_xz_mag = sqrt(u_ijC_x**2 + u_ijC_z**2)
       ! increment work:
       v_ijy0 = v_ijy
       v_ijy = v_jy - v_iy
       deltaW = 0.5 * deltaP * abs(v_ijy0 + v_ijy)
       W = W + deltaW
       if (W_c == huge(1.d0) .and. v_ijy > 0) then
          W_c = W
          W_f = (1 + e**2) * W_c
          ! PRINT *, "end of compression phase, W_c =", W, "deltaP = ", deltaP
       end if
    end do
    ! PRINT *, "end of restitution phase"
    v_i1 = MATMUL(G_T, (/ v_ix, v_iy, 0.d0 /))
    v_j1 = MATMUL(G_T, (/ v_jx, v_jy, 0.d0 /))
    omega_i1 = MATMUL(G_T, omega_i1)
    omega_j1 = MATMUL(G_T, omega_j1)
    ! if (sum(v_i1**2) < ZERO_VELOCITY_CLIP_SQRD) then
    !    if (abs(omega_i1(2)) < ZERO_ANGULAR_VELOCITY_CLIP) then
    !       PRINT *, "i -> BallRestEvent"
    !    else
    !       PRINT *, "i -> BallSpinningEvent"
    !    endif
    ! else
    !    u = calc_slip_velocity(v_i1, omega_i1)
    !    if (sum(u**2) < ZERO_VELOCITY_CLIP_SQRD) then
    !       PRINT *, "i -> BallRollingEvent"
    !    else
    !       a_i1 = calc_motion_coefficients(r_i, v_i, omega_i)
    !       PRINT *, "i -> BallSlidingEvent", a_i1
    !    endif
    ! endif
    ! if (sum(v_j1**2) < ZERO_VELOCITY_CLIP_SQRD) then
    !    if (abs(omega_j1(2)) < ZERO_ANGULAR_VELOCITY_CLIP) then
    !       PRINT *, "j -> BallRestEvent"
    !    else
    !       PRINT *, "j -> BallSpinningEvent"
    !    endif
    ! else
    !    u = calc_slip_velocity(v_j1, omega_j1)
    !    if (sum(u**2) < ZERO_VELOCITY_CLIP_SQRD) then
    !       PRINT *, "j -> BallRollingEvent"
    !    else
    !       PRINT *, "j -> BallSlidingEvent"
    !    endif
    ! endif

  END SUBROUTINE collide_balls

  function calc_slip_velocity(v, omega)
    implicit none
    real(c_double), dimension(3) :: calc_slip_velocity
    real(c_double), dimension(3), intent(in) :: v, omega
    calc_slip_velocity = v + R * (/ omega(3), 0.d0, -omega(1) /)
  end function calc_slip_velocity

  function calc_motion_coefficients(r, v, omega)
    implicit none
    real(c_double), dimension(3,3) :: calc_motion_coefficients
    real(c_double), dimension(3), intent(in):: r, v, omega
    real(c_double), dimension(3) :: u
    u = calc_slip_velocity(v, omega)
    calc_motion_coefficients(:,1) = r
    calc_motion_coefficients(:,2) = v
    calc_motion_coefficients(:,3) = -0.5 * mu_s * grav * u / sqrt(sum(u**2))
  end function calc_motion_coefficients

  SUBROUTINE print_params () BIND(C)
    WRITE(*,*)
    WRITE(*, FMT=1) M,R,e,mu_b,mu_s
    1 FORMAT("M=",E10.5, "  R=",E10.5, "  e=",E10.5, "  mu_b=",E10.5, "  mu_s=",E10.5)
  END SUBROUTINE PRINT_PARAMS

END MODULE COLLISIONS
