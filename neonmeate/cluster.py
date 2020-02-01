import math
import random
import sys
from gi.repository import GdkPixbuf


class Image:
    def __init__(self, pixbuf):
        self.pixbuf = pixbuf
        self.width = pixbuf.get_width()
        self.height = pixbuf.get_height()
        self.stride = pixbuf.get_rowstride()
        self.bytes = pixbuf.get_pixels()

    def initial_sample_count(self):
        return int(0.05 * self.height * self.width)

    def color(self, row, col):
        p = row * self.stride + col * 3
        return self.bytes[p], self.bytes[p + 1], self.bytes[p + 2]


class Cluster:
    def __init__(self, r, g, b):
        self.count = 1
        self.mean = [r, g, b]
        self.initial_mean = [r, g, b]

    @staticmethod
    def color_dist(r1, g1, b1, r2, g2, b2):
        return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)

    def color_as_hex(self):
        a = [int(round(n)) for n in self.mean]
        num = a[0] * (256 ** 2) + a[1] * 256 + a[2]
        s = f"{num:#06x}"
        return s[2:]

    def recalc_means(self, r, g, b):
        n = self.count
        m = n - 1
        self.mean[0] = (self.mean[0] * m + r) / n
        self.mean[1] = (self.mean[1] * m + g) / n
        self.mean[2] = (self.mean[2] * m + b) / n

    def recenter(self):
        self.count = 1
        self.initial_mean = list(self.mean)

    def mean_dist(self):
        return self.dist(self.mean[0], self.mean[1], self.mean[2])

    def dist(self, r, g, b):
        return Cluster.color_dist(r, g, b, self.initial_mean[0], self.initial_mean[1], self.initial_mean[2])

    def add(self, r, g, b):
        self.count += 1
        self.recalc_means(r, g, b)


def pixbuf_from_file(fileobj):
    maxedge = 100
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(fileobj.name)
    if pixbuf.get_height() > maxedge and pixbuf.get_width() > maxedge:
        pixbuf = pixbuf.scale_simple(maxedge, maxedge, GdkPixbuf.InterpType.BILINEAR)
    return pixbuf


def kmeans(k, img):
    # populate initial clusters
    coords = [(r, c) for r in list(range(img.height)) for c in list(range(img.width))]
    initial = random.sample(coords, k)
    clusters = []

    for row, col in initial:
        r, g, b = img.color(row, col)
        clusters.append(Cluster(r, g, b))

    i = 0
    dist = 1

    while dist >= 1:
        i += 1
        print(f"Pass {i}")

        for c in clusters:
            c.recenter()

        for row, col in coords:
            r, g, b = img.color(row, col)
            closest = None
            closest_dist = float('Inf')

            for c in clusters:
                d = c.dist(r, g, b)

                if d < closest_dist:
                    closest = c
                    closest_dist = d

            closest.add(r, g, b)

        dist = 0
        for c in clusters:
            dist = max(dist, c.mean_dist())

    return clusters


def output(imgpath, colors):
    s = "<!doctype html>"
    s += "<html>"
    s += '<head><style>div { margin: 1em; }</style></head>'
    s += '<body>'
    s += f'<div><img src="file://{imgpath}"></div>'
    for color in colors:
        s += f'<div style="background-color: #{color}; min-height: 200px; width=100%; border: 1px solid black;">&nbsp;</div>'
    s += '</body>'
    s += "</html>"
    with open("/tmp/clusters.html", 'w') as f:
        f.write(s)


def main(args):
    filepath = args[0]
    with open(filepath, 'rb') as f:
        pixbuf = pixbuf_from_file(f)
    assert pixbuf.get_bits_per_sample() == 8
    assert pixbuf.get_colorspace() == GdkPixbuf.Colorspace.RGB
    img = Image(pixbuf)
    clusters = kmeans(5, img)
    output(filepath, [c.color_as_hex() for c in clusters])


if __name__ == '__main__':
    random.seed(None)
    main(sys.argv[1:])
