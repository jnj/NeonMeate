import math
import random
import string
import sys
from gi.repository import GdkPixbuf


class SamplerStrategy:
    """
    Randomly samples.
    """

    def __init__(self, width, height):
        self.width = width
        self.height = height

    def take(self, n):
        return [(random.randrange(0, self.width), random.randrange(0, self.height)) for i in range(n)]


class GridSampler(SamplerStrategy):
    """
    Subsample by 1/10 factor.
    """

    def __init__(self, width, height):
        super(GridSampler, self).__init__(width, height)
        self.x_stride = int(width / 10.0)
        self.y_stride = int(height / 10.0)
        self.x = 0
        self.y = 0

    def take(self, n):
        a = []
        for x in range(0, self.width, self.x_stride):
            for y in range(0, self.height, self.y_stride):
                a.append((x, y))
        random.shuffle(a)
        return a


class Image:
    def __init__(self, pixbuf):
        self.pixbuf = pixbuf
        self.width = pixbuf.get_width()
        self.height = pixbuf.get_height()
        self.stride = pixbuf.get_rowstride()
        self.bytes = pixbuf.get_pixels()

    def color(self, row, col):
        p = row * self.stride + col * 3
        return self.bytes[p], self.bytes[p + 1], self.bytes[p + 2]


class Cluster:
    def __init__(self, label, r, g, b):
        self.label = label
        self.count = 1
        self.mean = [r, g, b]
        self.initial_mean = [r, g, b]

    @staticmethod
    def color_dist(r1, g1, b1, r2, g2, b2):
        return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)

    def distance(self, other):
        return self.dist(other.initial_mean[0], other.initial_mean[1], other.initial_mean[2])

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


def pixbuf_from_file(fileobj, maxedge=100):
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(fileobj.name)
    if pixbuf.get_height() > maxedge and pixbuf.get_width() > maxedge:
        pixbuf = pixbuf.scale_simple(maxedge, maxedge, GdkPixbuf.InterpType.BILINEAR)
    return pixbuf


def initialize_clusters(k, cluster_min_distance, img):
    clusters = []
    max_samples = int(0.6 * img.height * img.width)
    grid_sampler = GridSampler(img.width, img.height)
    rand_sampler = SamplerStrategy(img.width, img.height)

    def different_enough(r, g, b):
        return all(c.dist(r, g, b) > cluster_min_distance for c in clusters)

    def add_if(r, g, b):
        if different_enough(r, g, b) and len(clusters) < k:
            label = ''.join(random.sample(string.ascii_uppercase, 6))
            clusters.append(Cluster(label, r, g, b))

    for x, y in grid_sampler.take(100):  # the n param is ignored by grid sampler
        r, g, b = img.color(y, x)
        add_if(r, g, b)

    if len(clusters) == k:
        return clusters

    # try with random sampling
    for x, y in rand_sampler.take(max_samples):
        r, g, b = img.color(y, x)
        add_if(r, g, b)

    return clusters


def kmeans(k, cluster_threshold, img):
    i = 0
    dist_thresh = 1
    dist = dist_thresh
    clusters = initialize_clusters(k, cluster_threshold, img)
    #print(f"{len(clusters)} clusters.")
    while dist >= dist_thresh:
        i += 1
        #print(f"Pass {i}")

        for c in clusters:
            c.recenter()

        for x in range(img.width):
            for y in range(img.height):
                r, g, b = img.color(y, x)
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


def output(imgpath, clusters):
    s = "<!doctype html>"
    s += "\n<html>"
    s += '\n\t<head><style>div { margin: 1em; }</style></head>'
    s += '\n\t<body>'
    s += f'\n\t\t<div><img src="file://{imgpath}"></div>'
    for cluster in clusters:
        s += f'\n\t\t<div style="background-color: #{cluster.color_as_hex()}; min-height: 200px; width=100%; border: 1px solid black;">{cluster.label} {cluster.count} {str(cluster.dist_dict)}</div>'
    s += '\n\t</body>'
    s += "\n</html>"
    with open("/tmp/clusters.html", 'w') as f:
        f.write(s)


def clusterize(pixbuf):
    maxedge = 150
    if pixbuf.get_height() > maxedge and pixbuf.get_width() > maxedge:
        pixbuf = pixbuf.scale_simple(maxedge, maxedge, GdkPixbuf.InterpType.BILINEAR)
    assert pixbuf.get_bits_per_sample() == 8
    assert pixbuf.get_colorspace() == GdkPixbuf.Colorspace.RGB
    img = Image(pixbuf)
    clusters = sorted(kmeans(6, 60, img), key=lambda c: c.count)
    white = Cluster('white', 255, 255, 255)
    black = Cluster('white', 0, 0, 0)
    thresh = 50

    def black_or_white(c):
        return c.distance(white) < thresh or c.distance(black) < thresh

    clusters = [c for c in clusters if not black_or_white(c)]
    return clusters


def main(args):
    filepath = args[0]
    with open(filepath, 'rb') as f:
        pixbuf = pixbuf_from_file(f, maxedge=100)
    clusters = clusterize(pixbuf)
    for c in clusters:
        dist_dict = {}
        for d in clusters:
            if c is d:
                continue
            dist_dict[d.label] = c.dist(d.mean[0], d.mean[1], d.mean[2])
        c.dist_dict = dist_dict

    output(filepath, clusters)


if __name__ == '__main__':
    random.seed(None)
    main(sys.argv[1:])
