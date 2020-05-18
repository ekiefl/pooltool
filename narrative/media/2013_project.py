import math
from random import *
import numpy as np
import matplotlib
from matplotlib import pyplot as plt
from matplotlib import animation

def main():
    global m_ani
    ######################################################################
    '''
    The balls get sent to the translation matrix, which moves the balls slightly,
    and then sends them back to
    main. Then, the balls are sent to the collisions checker, which checks
    collisions, then sends the balls and the collisions which it detected to
    the resolver, which resolves the collisions and then returns the balls
    to the collision detector which returns the balls to the main. This
    process is iterated, as the conditions are currently set, 45000 times and
    10 trials of this are carried out.
    It is suggested you go make a sandwich or get a coffee if intending to
    iterate more than ~750,000 times total. 
    '''
    ######################################################################

    '''
    R is the radius of the balls, a is the midway distance between the center of mass of two adjacent balls,
    (a-R)=f is the largest possible pertubation of a ball so that no balls superimpose
    '''
    
    R = 3.0
    a = 3.02
    
    f = a - R

    #this loops 10 times = 10 trials
    y = 0
    if y < 5:
            

        '''
        r_ij is a random number between 0 and 1. There are 15 values for i (representing each ball) and 2 values for j
        (the first representing the magnitude of a random pertubation and a second
        representing the direction of the random pertubation)
        '''
        r_11 = random()
        r_12 = random()
        r_21 = random()
        r_22 = random()
        r_31 = random()
        r_32 = random()
        r_41 = random()
        r_42 = random()
        r_51 = random()
        r_52 = random()
        r_61 = random()
        r_62 = random()
        r_71 = random()
        r_72 = random()
        r_81 = random()
        r_82 = random()
        r_91 = random()
        r_92 = random()
        r_101 = random()
        r_102 = random()
        r_111 = random()
        r_112 = random()
        r_121 = random()
        r_122 = random()
        r_131 = random()
        r_132 = random()
        r_141 = random()
        r_142 = random()
        r_151 = random()
        r_152 = random()
        
        r_v = random()
        r_v2 = random()

        '''
        Each b_i is a ball, whose state is defined by 5 elements
        [xposition, yposition, xvelocity, yvelocity, indentifying#]

        The first terms in the xposition and yposition orient the balls
        in an equilateral triangle. The orientation of this triangle is the
        same as the triangle that this 'less than' and 'such that' sign
        make: <|

        The second terms in the xpos and ypos represent the pertubation of
        each ball, which ensures that there is no overlap between the balls

        The ball farthest left (b1) is given an initial velocity into the
        other balls.
        '''

        b1 = [0.0, 0.0 + f*r_11*math.sin(2*math.pi*r_12), 500.0, 50.+r_v2*100., 0]
        b2 = [math.sqrt(3)*a + f*r_21*math.cos(2*math.pi*r_22), -a + f*r_21*math.sin(2*math.pi*r_22), 0.0, 0.0, 1]
        b3 = [math.sqrt(3)*a + f*r_31*math.cos(2*math.pi*r_32), a + f*r_31*math.sin(2*math.pi*r_32), 0.0, 0.0, 2]
        b4 = [math.sqrt(3)*2.0*a + f*r_41*math.cos(2*math.pi*r_42), -2.0*a + f*r_41*math.sin(2*math.pi*r_42), 0.0, 0.0, 3]
        b5 = [math.sqrt(3)*2.0*a + f*r_51*math.cos(2*math.pi*r_52), a*0.0 + f*r_51*math.sin(2*math.pi*r_52), 0.0, 0.0, 4]
        b6 = [math.sqrt(3)*2.0*a + f*r_61*math.cos(2*math.pi*r_62), 2.0*a + f*r_61*math.sin(2*math.pi*r_62), 0.0, 0.0, 5]
        b7 = [math.sqrt(3)*3.0*a + f*r_71*math.cos(2*math.pi*r_72), -3.0*a + f*r_71*math.sin(2*math.pi*r_72), 0.0, 0.0, 6]
        b8 = [math.sqrt(3)*3.0*a + f*r_81*math.cos(2*math.pi*r_82), -a + f*r_81*math.sin(2*math.pi*r_82), 0.0, 0.0, 7]
        b9 = [math.sqrt(3)*3.0*a + f*r_91*math.cos(2*math.pi*r_92), a + f*r_91*math.sin(2*math.pi*r_92), 0.0, 0.0, 8]
        b10 = [math.sqrt(3)*3.0*a + f*r_101*math.cos(2*math.pi*r_102), 3.0*a + f*r_101*math.sin(2*math.pi*r_102), 0.0, 0.0, 9]
        b11 = [math.sqrt(3)*4.0*a + f*r_111*math.cos(2*math.pi*r_112), -4.0*a + f*r_111*math.sin(2*math.pi*r_112), 0.0, 0.0, 10]
        b12 = [math.sqrt(3)*4.0*a + f*r_121*math.cos(2*math.pi*r_122), -2.0*a + f*r_121*math.sin(2*math.pi*r_122), 0.0, 0.0, 11]
        b13 = [math.sqrt(3)*4.0*a + f*r_131*math.cos(2*math.pi*r_132), 0.0*a + f*r_131*math.sin(2*math.pi*r_132), 0.0, 0.0, 12]
        b14 = [math.sqrt(3)*4.0*a + f*r_141*math.cos(2*math.pi*r_142), 2.0*a + f*r_141*math.sin(2*math.pi*r_142), 0.0, 0.0, 13]
        b15 = [math.sqrt(3)*4.0*a + f*r_151*math.cos(2*math.pi*r_152), 4.0*a + f*r_151*math.sin(2*math.pi*r_152), 0.0, 0.0, 14]
        
        '''
        m is the master list of all pool balls
        '''
        
        m = [b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11, b12, b13, b14, b15]

        '''
        del_t is the time step

        if delta t is of order 0.00000001, higher precision number types are needed
        '''
        
        del_t = 0.00001
        
        print ""

        #this loop means 45000 iterations of translate, check for collisions,
        #and resolve collisions will be carried out

        i = 0
        NN = 500000
        div = 50
        m_ani = np.zeros((NN/div, 15, 5))  
        
        for i in range(0,NN):
            
            '''
            uncomment if you want to see the 10th balls velocity every 5000 iterations
            '''
            m = translation(m, del_t)
            m = collision_detector(m, del_t)
            
            if i%div == 0:
                m_ani[i/div,:,:] = np.asarray(m)
            
            #m_ani[i,:,:] = np.asarray(m)
    
    '''
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_xlim(-100,100)
    ax.set_ylim(-100,100)
    fig.set_dpi(100)
    particles, = ax.plot([], [], 'bo', ms=27)
    
    
    def init():
        particles.set_data([], [])
        return particles,
    
    def animate(i):
        global m_ani
        particles.set_data(m_ani[i,10,:], m_ani[i,10,:])  
        particles.set_markersize(3.)
        return particles,
    
    anim = animation.FuncAnimation(fig, animate, 
                                   init_func=init, 
                                   frames=360, 
                                   interval=20,
                                   blit=False)

    plt.show()
    '''
    '''
    print np.shape(m_ani)    
    upto = 5000
    
    fig = plt.figure()
    ax  = fig.add_subplot(111)
    ax.scatter(m_ani[0,:,0],m_ani[0,:,1],s=120,alpha=0.4)
    ax.plot(m_ani[:upto,:,0],m_ani[:upto,:,1])
    ax.scatter(m_ani[upto,:,0],m_ani[upto,:,1],s=120)
    ax.set_xlim(-180,60)
    ax.set_ylim(-60,60)
    plt.show()
    
    fig = plt.figure()
    ax  = fig.add_subplot(111)
    ax.scatter(m_ani[0,:,0],m_ani[0,:,1],s=120,alpha=0.4)
    ax.plot(m_ani[:2*upto,:,0],m_ani[:2*upto,:,1])
    ax.scatter(m_ani[2*upto,:,0],m_ani[2*upto,:,1],s=120)
    ax.set_xlim(-180,60)
    ax.set_ylim(-60,60)
    plt.show()
    
    fig = plt.figure()
    ax  = fig.add_subplot(111)
    ax.scatter(m_ani[0,:,0],m_ani[0,:,1],s=120,alpha=0.4)
    ax.plot(m_ani[:3*upto,:,0],m_ani[:3*upto,:,1])
    ax.scatter(m_ani[3*upto,:,0],m_ani[3*upto,:,1],s=120)
    ax.set_xlim(-180,60)
    ax.set_ylim(-60,60)
    plt.show()
    
    fig = plt.figure()
    ax  = fig.add_subplot(111)
    ax.scatter(m_ani[0,:,0],m_ani[0,:,1],s=120,alpha=0.4)
    ax.plot(m_ani[:4*upto,:,0],m_ani[:4*upto,:,1])
    ax.scatter(m_ani[4*upto,:,0],m_ani[4*upto,:,1],s=120)
    ax.set_xlim(-180,60)
    ax.set_ylim(-60,60)
    plt.show()
    
    fig = plt.figure()
    ax  = fig.add_subplot(111)
    ax.scatter(m_ani[0,:,0],m_ani[0,:,1],s=120,alpha=0.4)
    ax.plot(m_ani[:5*upto,:,0],m_ani[:5*upto,:,1])
    ax.scatter(m_ani[5*upto,:,0],m_ani[5*upto,:,1],s=120)
    ax.set_xlim(-180,60)
    ax.set_ylim(-60,60)
    plt.show()
    '''
    
    cm = matplotlib.cm.get_cmap('Set1')
    colors=[cm(1.*i/15) for i in range(15)]
    xy = range(15)
    colorlist=[colors[x/2] for x in xy]
    
    
    fig = plt.figure()
    ax = plt.axes(xlim=(-180, 60), ylim=(-60, 60))
    ax.scatter(m_ani[0,:,0],m_ani[0,:,1],s=300,c=colorlist,alpha=0.3)
    line,    = ax.plot([], [], lw=2)
    scat     = ax.scatter([], [], s = 300,c=colorlist)
    
    def init():
        scat.set_offsets([])
        line.set_data([], [])
        return scat, line
    
    def animate(i):
        x = m_ani[5*i,:,0]; y = m_ani[5*i,:,1]
        x2 = m_ani[:5*i,0,0]; y2 = m_ani[:5*i,0,1]
        data = np.hstack((x[:5*i,np.newaxis], y[:5*i, np.newaxis]))
        scat.set_offsets(data)
        line.set_data(x2, y2)
        return scat, line
        
    anim = animation.FuncAnimation(fig, animate, init_func=init,
                               frames=NN/div/5, interval=1, blit=False)
                               
                               
                               
    print 'done'
    plt.show()
    
    
    y += 1
    
    m = np.asarray(m)
    print np.shape(m)
    
    
    
    
        
        
        
def collision_detector(m, del_t):

    '''
    collisions looks at the distance from one ball's center
    of mass to another ball's center of mass and determines
    whether the distance is less than twice the radius of the
    balls. Additionally, to avoid successive collisions between
    the same two balls, it checks whether or not the balls
    are moving toward each other. These two conditions define
    a collision.
    '''

    '''
    c is a list which collisions creates that pairs colliding
    balls. c is then sent to the collision resolver
    '''
    
    c = []
    
    R = 3.0
    
    for i in m:
        for j in m:
            if j > i:        
                if math.sqrt((i[0]-j[0])**2 + (i[1]-j[1])**2) < 2*R:
                    if math.sqrt((i[0]-j[0]-del_t*(i[2]-j[2]))**2 + (i[1]-j[1]-del_t*(i[3]-j[3]))**2) > math.sqrt((i[0]-j[0])**2 + (i[1]-j[1])**2):
                        c.append([i,j])
                        '''
                        comment out if you want to see what is colliding with what, as collisions occur
                        
                        print i[4], "with ", j[4]
                        '''
    m = resolver(m,c)
    return m

def resolver(m,c):

    '''
    The resolver takes 2 balls in c which have been determined to collide,
    and changes the frame of reference so that one of them is at rest.
    By doing this, one can use the principle that the ball initially with
    zero velocity have a final velocity in the same direction as the vector
    that connects the balls' center of masses. Additionally, the impacting ball's
    final velocity will be in a direction orthogonal to this direction. This
    resolver basically creates these direction vectors, and then projects
    the initial velocity of the incoming ball onto these vectors to determine
    the final velocities. After that is done, the translational velocity
    that was subtracted to make one of the velocities zero is added back, and
    then these new velocities are updated into the master list.
    '''

    for i in c:

        k_1x = i[0][0] - i[1][0]
        k_1y = i[0][1] - i[1][1]
        k_2x = i[1][1] - i[0][1]
        k_2y = i[0][0] - i[1][0]

        rel_vel_x = i[0][2]
        rel_vel_y = i[0][3]
        
        
        i[1][2] = i[1][2] - i[0][2] #v2x after frame of reference change
        i[0][2] = i[0][2] - i[0][2] #v1x
        i[1][3] = i[1][3] - i[0][3] #v2y
        i[0][3] = i[0][3] - i[0][3] #v1y

        k2dotv = (i[1][1] - i[0][1])*i[1][2] + (i[0][0] - i[1][0])*i[1][3]
        k1dotv = (i[0][0] - i[1][0])*i[1][2] + (i[0][1] - i[1][1])*i[1][3]

        i[0][2] = k1dotv/(k_1x**2 + k_1y**2)*k_1x + rel_vel_x #v1xf
        i[0][3] = k1dotv/(k_1x**2 + k_1y**2)*k_1y + rel_vel_y #v1yf
        i[1][2] = k2dotv/(k_2x**2 + k_2y**2)*k_2x + rel_vel_x #v2xf
        i[1][3] = k2dotv/(k_2x**2 + k_2y**2)*k_2y + rel_vel_y #v2yf

        m[i[0][4]] = i[0]
        m[i[1][4]] = i[1]

    

    return m

def translation(m, del_t):

    '''
    In pseudocode, this function reads as:
    
    for every ball:
        x = x_0 + v_x * delta_t
        y = y_0 + v_y * delta_t

        if ball hits rail, reverse respective velocity component
    '''
        
    
    for b in m:
        b[0] = b[0] + del_t*b[2]
        b[1] = b[1] + del_t*b[3]
        if b[1] > 60.0 and b[3] > 0:
            b[3] = -b[3]
        if b[1] < -60.0 and b[3] < 0:
            b[3] = -b[3]
        if b[0] > 60.0 and b[2] > 0:
            b[2] = -b[2]
        if b[0] < -180 and b[2] < 0:
            b[2] = -b[2]
        
    
    return m

main()
                    
