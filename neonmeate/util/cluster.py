import random
import string
import sys

from gi.repository import GdkPixbuf

from neonmeate.util.color import RGBColor


def triplet_mean(elements):
    n = len(elements)

    if n == 0:
        return 0, 0, 0

    a = sum(x for x, _, _ in elements)
    b = sum(y for _, y, _ in elements)
    c = sum(z for _, _, z in elements)

    return a / n, b / n, c / n


def pixbuf_from_file(fileobj):
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(fileobj.name)
    return pixbuf


def cluster_rgb(cluster):
    h, s, v = cluster.mean()
    return RGBColor.from_hsv(h, s, v)


class SamplerStrategy:
    """
    Randomly samples.
    """

    def __init__(self, width, height, rng):
        self.width = width
        self.height = height
        self.rng = rng

    def take(self, n):
        return [(self.rng.randrange(0, self.width), self.rng.randrange(0, self.height)) for i in range(n)]


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

    def __init__(self, label, initial_value, dist_fn, mean_fn):
        self.label = label
        self.dist_fn = dist_fn
        self.mean_fn = mean_fn
        self.elements = [initial_value]
        self.cached_mean = self.mean()
        self.count = 1

    def update_cached_mean(self, mean):
        self.elements = [mean]
        self.cached_mean = self.mean()

    def mean(self):
        n = len(self.elements)
        self.count = n
        return self.mean_fn(self.elements)

    def add(self, element):
        self.elements.append(element)


class ColorClusterer:
    def __init__(self, num_clusters, cluster_threshold, rng):
        self._desired_clusters = num_clusters
        self._cluster_threshold = cluster_threshold
        self._cluster_distance_threshold = 0.00005
        self._max_init_cluster_iterations = 50
        self._rng = rng
        self.rounds = []
        self.clusters = []
        self.dist_fn = RGBColor.norm_hsv_dist

    def reset(self):
        self.clusters = []

    def _different_enough(self, col):
        for c in self.clusters:
            m = c.cached_mean
            if self.dist_fn(col[0], col[1], col[2], m[0], m[1], m[2]) >= self._cluster_distance_threshold:
                return False
        return True

    def _init_clusters(self, img):
        i = 0
        k = self._desired_clusters
        max_samples = int(0.75 * img.height * img.width)
        rand_sampler = SamplerStrategy(img.width, img.height, self._rng)

        while len(self.clusters) < k and i < self._max_init_cluster_iterations:
            for x, y in rand_sampler.take(max_samples):
                col = RGBColor.from_256(*img.color(y, x)).to_norm_hsv()
                if self._different_enough(col):
                    label = ''.join(self._rng.sample(string.ascii_uppercase, 6))
                    c = Cluster(label, col, self.dist_fn, triplet_mean)
                    self.clusters.append(c)
                    if len(self.clusters) == k:
                        break
            i += 1

    @staticmethod
    def each_img_color(img):
        for x in range(img.width):
            for y in range(img.height):
                hsv = RGBColor.from_256(*img.color(y, x)).to_norm_hsv()
                yield hsv

    def _add_to_nearest(self, color):
        near = None
        dist = float('Inf')

        for cluster in self.clusters:
            m = cluster.cached_mean
            d = cluster.dist_fn(m[0], m[1], m[2], color[0], color[1], color[2])
            if d < dist:
                near = cluster
                dist = d

        near.add(color)

    def cluster(self, img):
        self._init_clusters(img)

        if len(self.clusters) < 2:
            return

        maxiters = 50
        itercount = 0
        thresh = self._cluster_distance_threshold

        while itercount < maxiters:
            orig_means = [c.mean() for c in self.clusters]
            round = [cluster_rgb(c) for c in self.clusters]
            self.rounds.append(round)

            for hsv in ColorClusterer.each_img_color(img):
                self._add_to_nearest(hsv)

            new_means = [c.mean() for c in self.clusters]

            if all(self.dist_fn(u[0], u[1], u[2], v[0], v[1], v[2]) < thresh for u, v in zip(orig_means, new_means)):
                break

            for mean, cluster in zip(new_means, self.clusters):
                cluster.update_cached_mean(mean)

            itercount += 1


def output(imgpath, clusters, rounds):
    s = "<!doctype html>"
    s += "\n<html>"
    s += '\n\t<head><style>div { margin: 1em; } #gradArt { width: 700px; height: 700px; }</style></head>'
    s += '\n\t<body>'
    s += f'\n\t\t<div><img src="file://{imgpath}"></div>'

    for i, rgbs in enumerate(rounds):
        s += f"<div><h3>Round {i + 1}</h3>"
        for rgb in rgbs:
            r = round(rgb.rgb[0] * 100.0, 2)
            g = round(rgb.rgb[1] * 100.0, 2)
            b = round(rgb.rgb[2] * 100.0, 2)
            s += f'\n\t\t<div style="background-color: rgb({r}%,{g}%,{b}%); min-height: 100px; width=100px; border: 1px solid black;"></div>'
        s += "</div>"

    for cluster in clusters:
        rgb = cluster_rgb(cluster)
        r = round(rgb.rgb[0] * 100.0, 2)
        g = round(rgb.rgb[1] * 100.0, 2)
        b = round(rgb.rgb[2] * 100.0, 2)
        s += f'\n\t\t<div style="background-color: rgb({r}%,{g}%,{b}%); min-height: 200px; width=100%; border: 1px solid black;">{cluster.label} <h1>Count: {cluster.count}</h1> {str(cluster.dist_dict)}</div>'

    s += "<div id=\"gradArt\">"

    s += "</div>"
    s += '\n\t</body>'
    s += "\n</html>"
    with open("/tmp/clusters.html", 'w') as f:
        f.write(s)


def clusterize(pixbuf, rng):
    maxedge = 200
    assert pixbuf.get_bits_per_sample() == 8
    assert pixbuf.get_colorspace() == GdkPixbuf.Colorspace.RGB

    if pixbuf.get_height() > maxedge and pixbuf.get_width() > maxedge:
        pixbuf = pixbuf.scale_simple(maxedge, maxedge, GdkPixbuf.InterpType.BILINEAR)

    img = Image(pixbuf)
    clusterer = ColorClusterer(4, 0.008, rng)
    clusterer.cluster(img)
    clusters = clusterer.clusters

    dist = RGBColor.norm_hsv_dist
    white = Cluster('white', RGBColor(1, 1, 1).to_norm_hsv(), dist, triplet_mean)
    black = Cluster('black', RGBColor(0, 0, 0).to_norm_hsv(), dist, triplet_mean)
    bw_thresh = 0.0107

    def black_or_white(c):
        w = white.cached_mean
        b = black.cached_mean
        m = c.cached_mean
        dw = dist(m[0], m[1], m[2], w[0], w[1], w[2])
        if dw < bw_thresh:
            return True
        db = dist(m[0], m[1], m[2], b[0], b[1], b[2])
        if db < bw_thresh:
            # print(f'yes, is white or black')
            return True
        return False

    clusters = [c for c in clusters if not black_or_white(c)]
    kept = set()
    l = len(clusters)

    for i in range(l):
        c = clusters[i]
        kept.add(c.label)
        for j in range(i + 1, l):
            d = clusters[j]
            if not similar(c, d):
                kept.add(d.label)

    return sorted([c for c in clusters if c.label in kept], key=lambda c: c.count, reverse=True), clusterer.rounds


class ClusteringResult:
    def __init__(self, clusters):
        self.clusters = clusters

    def dominant(self):
        c = cluster_rgb(self.clusters[0])
        if c.almost_black():
            return c.lighten(10)
        return c

    def complementary(self):
        l = len(self.clusters)
        if l == 1:
            return cluster_rgb(self.clusters[0]).alter()
        elif l <= 2:
            return cluster_rgb(self.clusters[1])
        else:
            return cluster_rgb(self.clusters[-2])


def similar(clust1, clust2):
    cm = clust1.cached_mean
    dm = clust2.cached_mean
    return RGBColor.norm_hsv_dist(cm[0], cm[1], cm[2], dm[0], dm[1], dm[2]) < 0.05


def main(args):
    import time

    filepath = args[0]
    with open(filepath, 'rb') as f:
        pixbuf = pixbuf_from_file(f)
    rng = random.Random()
    rng.seed(int(1000 * time.time()))

    clusters, rounds = clusterize(pixbuf, rng)
    for c in clusters:
        dist_dict = {}
        for d in clusters:
            if c is d:
                continue
            dist_dict[d.label] = RGBColor.norm_hsv_dist(
                c.cached_mean[0], c.cached_mean[1], c.cached_mean[2],
                d.cached_mean[0], d.cached_mean[1], d.cached_mean[2]
            )
        c.dist_dict = dist_dict

    output(filepath, clusters, rounds)


if __name__ == '__main__':
    main(sys.argv[1:])
