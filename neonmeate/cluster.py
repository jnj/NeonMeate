import random
import string
import sys

from gi.repository import GdkPixbuf
from neonmeate.color import RGBColor


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
    Subsample in a grid pattern.
    """

    def __init__(self, width, height):
        super(GridSampler, self).__init__(width, height)
        self.x_stride = max(int(width / 5.0), 5)
        self.y_stride = max(int(height / 5.0), 5)
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
    def __init__(self, label, rgbcolor):
        self.rgbcolor = rgbcolor
        self.label = label
        self.count = 1
        self.mean = list(rgbcolor.rgb)
        self.initial_mean = list(self.mean)

    def __str__(self):
        return f'Cluster[count={self.count}, rgb={self.mean_as_rgbcolor()}]'

    def distance(self, other):
        a = RGBColor(*self.initial_mean)
        b = RGBColor(*other.initial_mean)
        return a.hsv_distance(b)

    def mean_as_rgbcolor(self):
        return RGBColor(*self.mean)

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
        return self.dist(RGBColor(self.mean[0], self.mean[1], self.mean[2]))

    def dist(self, col):
        return self.rgbcolor.hsv_distance(col)

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
    maxiters = 10
    itercount = 0
    max_samples = int(0.75 * img.height * img.width)
    grid_sampler = GridSampler(img.width, img.height)
    rand_sampler = SamplerStrategy(img.width, img.height)

    while len(clusters) < k and itercount < maxiters:
        def different_enough(col):
            return all(c.dist(col) > cluster_min_distance for c in clusters)

        def add_if(c):
            if different_enough(c) and len(clusters) < k:
                label = ''.join(random.sample(string.ascii_uppercase, 6))
                clusters.append(Cluster(label, c))
                return True
            return False

        for x, y in grid_sampler.take(100):  # the n param is ignored by grid sampler
            r, g, b = img.color(y, x)
            rgbcol = RGBColor.from_256(r, g, b)
            if add_if(rgbcol):
                pass
        if len(clusters) == k:
            return clusters

        # try with random sampling
        for x, y in rand_sampler.take(max_samples):
            r, g, b = img.color(y, x)
            rgbcol = RGBColor.from_256(r, g, b)
            if add_if(rgbcol) and len(clusters) >= k:
                break

        itercount += 1

    return clusters


def kmeans(k, cluster_threshold, img):
    i = 0
    dist_thresh = 1
    dist = dist_thresh
    clusters = initialize_clusters(k, cluster_threshold, img)
    maxiters = 50
    itercount = 0

    while dist >= dist_thresh and itercount < maxiters:
        i += 1
        itercount += 1

        for c in clusters:
            c.recenter()

        for x in range(img.width):
            for y in range(img.height):
                r, g, b = img.color(y, x)
                rgbcol = RGBColor.from_256(r, g, b)
                closest = None
                closest_dist = float('Inf')

                for c in clusters:
                    d = c.dist(rgbcol)

                    if d < closest_dist:
                        closest = c
                        closest_dist = d

                closest.add(*rgbcol.rgb)

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
        r = round(cluster.mean[0] * 100.0, 2)
        g = round(cluster.mean[1] * 100.0, 2)
        b = round(cluster.mean[2] * 100.0, 2)
        s += f'\n\t\t<div style="background-color: rgb({r}%,{g}%,{b}%); min-height: 200px; width=100%; border: 1px solid black;">{cluster.label} {cluster.count} {str(cluster.dist_dict)}</div>'
    s += '\n\t</body>'
    s += "\n</html>"
    with open("/tmp/clusters.html", 'w') as f:
        f.write(s)


def clusterize(pixbuf):
    maxedge = 150
    assert pixbuf.get_bits_per_sample() == 8
    assert pixbuf.get_colorspace() == GdkPixbuf.Colorspace.RGB
    if pixbuf.get_height() > maxedge and pixbuf.get_width() > maxedge:
        pixbuf = pixbuf.scale_simple(maxedge, maxedge, GdkPixbuf.InterpType.BILINEAR)

    img = Image(pixbuf)
    clusters = sorted(kmeans(6, 0.0075, img), key=lambda c: c.count)

    white = Cluster('white', RGBColor(1, 1, 1))
    black = Cluster('white', RGBColor(0, 0, 0))
    bw_thresh = 0.01

    def black_or_white(c):
        return c.distance(white) < bw_thresh or c.distance(black) < bw_thresh

    clusters = [c for c in clusters if not black_or_white(c)]
    return clusters


def main(args):
    filepath = args[0]
    with open(filepath, 'rb') as f:
        pixbuf = pixbuf_from_file(f, maxedge=70)
    clusters = clusterize(pixbuf)
    for c in clusters:
        dist_dict = {}
        for d in clusters:
            if c is d:
                continue
            dist_dict[d.label] = c.dist(RGBColor(*d.mean))
        c.dist_dict = dist_dict

    output(filepath, clusters)


if __name__ == '__main__':
    random.seed(39334)
    main(sys.argv[1:])
