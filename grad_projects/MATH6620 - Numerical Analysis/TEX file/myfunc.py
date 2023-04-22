def f(t,y):
    y1 = y[0]
    y2 = y[1]

    dy1 = -4 * y1 + 3 * y2 + 6
    dy2 = -2.4 * y1 + 1.6 * y2 + 3.6
    dy = np.array([dy1, dy2])

    return dy

def true_f(t):
    from numpy import exp
    
    yt1 = -3.375*exp(-2*t) + 1.875*exp(-0.4*t) + 1.5
    yt2 = -2.25*exp(-2*t) + 2.25*exp(-0.4*t)
    
    return (yt1, yt2)
