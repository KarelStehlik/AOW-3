from math import sqrt


def calc(a1, b1, a2, b2, x, y, r):
    # [a1,b1] = start of line
    # [a2, b2] = end of line
    # [x, y] = centre of circle
    # r = radius of circle
    t1 = a1 - x
    t2 = a2 - a1
    t3 = b1 - y
    t4 = b2 - b1
    c = t1 * t1 + t3 * t3 - r * r
    b = 2 * t1 * t2 + 2 * t3 * t4
    a = t2 * t2 + t4 * t4
    D = b * b - 4 * a * c
    if D < 0:
        return None
    sqrtd = sqrt(D)
    k1 = (-b + sqrtd) * (2 * a)
    k2 = (-b - sqrtd) * (2 * a)
    k1 = max(min(1, k1), 0)
    k2 = max(min(1, k2), 0)
    return [[a1 + k1 * (a2 - a1), b1 + k1 * (b2 - b1)], [a1 + k2 * (a2 - a1), b1 + k2 * (b2 - b1)]]
