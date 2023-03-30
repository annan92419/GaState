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
