def almostEqual(a, b, thresh=0.01):
    return a <= b + thresh * abs(b) and a >= b - thresh * abs(b)
