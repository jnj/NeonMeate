import colorsys
import math


class RGBColor:

    @staticmethod
    def from_256(r, g, b):
        s = 255.0
        return RGBColor(r / s, g / s, b / s)

    def __init__(self, r, g, b):
        self.rgb = [r, g, b]

    def __str__(self):
        return str(self.rgb)

    def darken(self, percent):
        change = percent * 0.01
        h, s, v = colorsys.rgb_to_hsv(*self.rgb)
        return RGBColor(*colorsys.hsv_to_rgb(h, s, max(0, v - change)))

    def euclidean_rgb_distance(self, other):
        return math.sqrt(sum([(self.rgb[i] - other.rgb[i]) ** 2 for i in range(3)]))

    def to_norm_hsv(self):
        h, s, v = colorsys.rgb_to_hsv(*self.rgb)
        return math.pi * 2 * h, s, v

    def hsv_distance(self, other):
        h1, s1, v1 = self.to_norm_hsv()
        h2, s2, v2 = other.to_norm_hsv()
        return (math.sin(h1) * s1 * v1 - math.sin(h2) * s2 * v2) ** 2 + \
               (math.cos(h1) * s1 * v1 - math.cos(h2) * s2 * v2) ** 2 + \
               (v1 - v2) ** 2
