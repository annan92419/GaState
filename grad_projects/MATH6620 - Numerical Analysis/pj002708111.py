import numpy as np

def euler(f, a, b, ya, N):
    n = len(ya)
    h = (b - a) / N
    t = np.arange(a,b+h,h)
    y = np.zeros((n,N+1))
    
    t[0] = a
    y[:,0] = ya

    for i in range(N):
        y[:,i+1] = y[:,i] + h*f(t[i], y[:,i])

    return (t, y)



def mod_euler(f, a, b, ya, N):
    n = len(ya)
    h = (b - a) / N
    t = np.arange(a,b+h,h)
    y = np.zeros((n,N+1))
    
    t[0] = a
    y[:,0] = ya 

    for i in range(N):
        k = f(t[i], y[:,i])
        y[:,i+1] = y[:,i] + (h/2) * (k + f(t[i+1], y[:,i] + h*k))

    return (t, y)



def rk2(f, a, b, ya, N):
    n = len(ya)
    h = (b - a) / N
    t = np.arange(a,b+h,h)
    y = np.zeros((n,N+1))
    
    t[0] = a
    y[:,0] = ya 

    for i in range(N):
        k1 = f(t[i], y[:,i])
        k2 = f(t[i] + h/2, y[:,i] + (h/2)*k1)
        y[:,i+1] = y[:,i] + h*k2 

    return (t, y)



def rk4(f, a, b, ya, N):
    n = len(ya)
    h = (b - a) / N
    t = np.arange(a,b+h,h)
    y = np.zeros((n,N+1))
    
    t[0] = a
    y[:,0] = ya 

    for i in range(N):
        k1 = f(t[i], y[:,i])
        k2 = f(t[i] + h/2, y[:,i] + (h/2)*k1)
        k3 = f(t[i] + h/2, y[:,i] + (h/2)*k2)
        k4 = f(t[i+1], y[:,i] + h*k3)
        k = k1 + 2*k2 + 2*k3 + k4
        y[:,i+1] = y[:,i] + (h/6) * k

    return (t, y)
    


def adams_explicit4(f, a, b, ya, N):
    t, y = rk4(f, a, b, ya, N)

    h = (b - a) / N
    
    for i in range(3,N):
        k0 = f(t[i], y[:,i])
        k1 = f(t[i-1], y[:,i-1])
        k2 = f(t[i-2], y[:,i-2])
        k3 = f(t[i-3], y[:,i-3])
        k = 55*k0 - 59*k1 + 37*k2 - 9*k3
        y[:,i+1] = y[:,i] + h/24 * k
    
    return (t, y)



def adams_pc4(f, a, b, ya, N):
    t, y = rk4(f, a, b, ya, N)

    h = (b - a) / N
    
    for i in range(3,N):
        k0 = f(t[i], y[:,i])
        k1 = f(t[i-1], y[:,i-1])
        k2 = f(t[i-2], y[:,i-2])
        k3 = f(t[i-3], y[:,i-3]) 
        y[:,i+1] = y[:,i] + h/24 * (55*k0 - 59*k1 + 37*k2 - 9*k3)
        k = f(t[i+1], y[:,i+1])
        y[:,i+1] = y[:,i] + h/24 * (9*k + 19*k0 - 5*k1 + k2)
    
    return (t, y)
   


def rkf(f, a, b, ya, TOL, hmin, hmax):
    n = len(ya)
    h = hmax
    t = [a]
    y = ya
    
    i = 0
    flag = True
    while flag:
        k1 = h * f(t[i], y[:,i])
        k2 = h * f(t[i] + 1/4*h, y[:,i] + 1/4*k1)
        k3 = h * f(t[i] + 3/8*h, y[:,i] + 3/32*k1 + 9/32*k2)
        k4 = h * f(t[i] + 12/13*h, y[:,i] + 1932/2197*k1 - 7200/2197*k2 + 7296/2197*k3)
        k5 = h * f(t[i] + h, y[:,i] + 439/216*k1 - 8*k2 + 3680/513*k3 - 845/4104*k4)
        k6 = h * f(t[i]  + 1/2*h, y[:,i] - 8/27*k1 + 2*k2 - 3544/2565*k3 + 1859/4104*k4 - 11/40*k5)

        R = 1/h * np.abs(1/360*k1 - 128/4275*k3 - 2197/75240*k4 + 1/50*k5 + 2/55*k6)

        if R <= TOL:
            t[i+1] = t[i] + h
            y[:,i+1] = y[:,i] + 25/216*k1 + 1408/2565*k3 + 2197/4104*k4 - 1/5*k5
            return (t, y, h)

        delta = .84 * (TOL / R) ** 1/4
        if delta <= 0.1:
            h = 0.1 * h
        elif delta >= 4:
            h = 4 * h
            h = delta * h # calculates new h

        if h > hmax:
            h = hmax

        if t >= b:
            flag = False
        elif t + h > b:
            h = b - t
        elif h < hmin:
            flag = False
            print('Minimum h exceeded; Procedure completed unsuccesfully!')
        
        i += 1

    print('The Procedure is complete!')
    
    

def adams_vs(f, a, b, ya, TOL, hmin, hmax):

    def RK4(f, h, y0, t0, y1=0, t1=0, y2=0, t2=0, y3=0, t3=0):
        y = [y0, y1, y2, y3]
        t = [t0, t1, t2, t3]
        for j in range(1,4):
            k1 = h * f(t[j-1], y[j-1])
            k2 = h * f(t[j-1] + h/2, y[j-1] + (1/2)*k1)
            k3 = h * f(t[j-1] + h/2, y[j-1] + (1/2)*k2)
            k4 = h * f(t[j-1] + h, y[j-1] + k3)
            k = k1 + 2*k2 + 2*k3 + k4
            y[j] = y[j-1] + (1/6) * k
            t[j] = t[0] + j*h
        return (t, y)
    
    t0, h = a, hmax
    y0 = ya
    flag, last = True, False
    t, y = RK4(f, h, y0, t0)
    nflag = True
    i = 4
    tn = t[3] + h # if accepted, t[4] = tn
    t.append(None)
    y.append(None)
    while flag:
        ypred = y[i-1] + h/24 * ( 55*f(t[i-1], y[i-1]) - 59*f(t[i-2], y[i-2]) + 37*f(t[i-3], y[i-3]) - 9*f(t[i-4], y[i-4]) )
        ycorr = y[i-1] + h/24 * ( 9*f(tn, ypred) + 19*f(t[i-1], y[i-1]) - 5*f(t[i-2], y[i-2]) + f(t[i-3], y[i-3]) )
        err = 19 * np.abs(ycorr - ypred) / 270*h
        if err <= TOL: # 7-16; accept
            y[i] = ycorr
            t[i] = tn
            if nflag == True:
                for j in range(i-3,i+1,1):
                    return (t, y, h)
            else:
                return (t, y, h)
            if last == True:
                flag = False
            else: # 10-16
                i += 1
                nflag = False
                if (err <= .1*TOL) or (t[i-1] + h > b): # 12 - 16
                    q = (TOL / 2*err) ** (1/4)
                    if q > 4:
                        h = 4*h
                    else:
                        h = q*h
                    if h > hmax:
                        h = hmax
                    if t[i-1] + 4*h > b:
                        h = (b - t[i-1])/4
                        last = True
                    tn, yn = RK4(f, h, y[i-1], t[i-1], y[i], t[i], y[i+1], t[i+1], y[i+2], t[i+2])
                    t.append(tn)
                    y.append(yn)
                    i += 3
        else: # 17-19; reject
            q = (TOL / 2*err) ** (1/4)
            if q < .1:
                h = .1 * h
            else:
                h = q * h
            if h < hmin:
                flag = False
                print('hmin exceeded')
            else:
                if nflag == True:
                    i -= 3
                    tn, yn = RK4(f, h, y[i-1], t[i-1], y[i], t[i], y[i+1], t[i+1], y[i+2], t[i+2])
                    i += 3
                    nflag = True 
        t = t[i-1] + h
        
    return (t, y, h)
