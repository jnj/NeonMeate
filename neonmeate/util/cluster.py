import random
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

    def __init__(self, label, initial_value, mean_fn, colorspace):
        self._colorspace = colorspace
        self.label = label
        self.dist_fn = colorspace.distance
        self.mean_fn = mean_fn
        self._centroid = initial_value
        self.elements = []
        self._count = 0

    def count(self):
        return self._count

    def distance(self, color):
        e = self._centroid
        return self.dist_fn(color[0], color[1], color[2], e[0], e[1], e[2])

    def centroid(self):
        return self._centroid

    def recalc_centroid(self):
        if self.elements:
            self._count = len(self.elements)
            self._centroid = self._mean()
            self.elements = []

    def _mean(self):
        return self.mean_fn(self.elements)

    def add(self, element):
        self.elements.append(element)

    def similar(self, clust2, threshold=0.01):
        dm = clust2.centroid()
        return self.distance(dm) < threshold


class RGBColorSpace:

    @staticmethod
    def distance(r1, g1, b1, r2, g2, b2):
        return RGBColor.rgb_euclidean_dist(r1, g1, b1, r2, g2, b2)

    @staticmethod
    def as_3_tuple(rgbcolor):
        return rgbcolor.components()

    @staticmethod
    def to_rgb_256_tuple(a, b, c):
        return RGBColor(a, b, c).to_256()

    @staticmethod
    def to_rgbcolor(a, b, c):
        return RGBColor(a, b, c)


class HSVColorSpace:

    @staticmethod
    def distance(h1, s1, v1, h2, s2, v2):
        return RGBColor.norm_hsv_dist(h1, s1, v1, h2, s2, v2)

    @staticmethod
    def as_3_tuple(rgbcolor):
        return rgbcolor.to_norm_hsv()

    @staticmethod
    def to_rgb_256_tuple(a, b, c):
        return RGBColor.from_hsv(a, b, c).to_256()

    @staticmethod
    def to_rgbcolor(a, b, c):
        return RGBColor.from_hsv(a, b, c)


class ColorClusterer:

    @staticmethod
    def color_at(img, x, y, colorspace):
        rgbcolor = RGBColor.from_256(*img.color(y, x))
        return colorspace.as_3_tuple(rgbcolor)

    def __init__(self, num_clusters, cluster_threshold, rng, max_iters, space):
        self._k = num_clusters
        self._max_iters = max_iters
        self._max_init_cluster_iterations = 100
        self._cluster_threshold = cluster_threshold
        self._colorspace = space
        self._rng = rng
        self.rounds = []
        self.clusters = []
        self.cluster_assignments = {}

    def _init_clusters(self, img):
        def getcolor(px, py):
            return ColorClusterer.color_at(img, px, py, self._colorspace)

        x, y = self._rng.randrange(0, img.width), self._rng.randrange(0, img.height)
        cluster = Cluster(f'Cluster 0', getcolor(x, y), triplet_mean, self._colorspace)
        self.clusters.append(cluster)

        points = []
        cluster_points = {(x, y)}

        def nearest(point):
            a, b = point
            return self._nearest_cluster(getcolor(a, b))

        for x in range(img.width):
            for y in range(img.height):
                points.append((x, y))

        while len(self.clusters) < self._k:
            max_dsquared = float('-inf')
            max_p = None
            for p in points:
                if p not in cluster_points:
                    x, y = p
                    closest = nearest(p)
                    col = getcolor(x, y)
                    d = closest.distance(col)
                    ds = d * d
                    if ds > max_dsquared:
                        max_dsquared = ds
                        max_p = p
            i = len(self.clusters)
            cent = Cluster(f'Cluster {i}', getcolor(max_p[0], max_p[1]), triplet_mean, self._colorspace)
            self.clusters.append(cent)
            cluster_points.add(max_p)

    @staticmethod
    def each_img_color(img, colorspace):
        for x in range(img.width):
            for y in range(img.height):
                yield x, y, colorspace.as_3_tuple(RGBColor.from_256(*img.color(y, x)))

    def _nearest_cluster(self, color):
        n = None
        d = float('Inf')

        for c in self.clusters:
            m = c.centroid()
            dist = c.dist_fn(m[0], m[1], m[2], color[0], color[1], color[2])
            if dist < d:
                n = c
                d = dist

        return n

    def _add_to_nearest(self, color):
        near = self._nearest_cluster(color)
        near.add(color)
        return near

    def _merge_similar(self):
        merged_any = True
        while merged_any:
            merged_any = False
            cluster = self.clusters[0]
            to_merge = []
            for other in self.clusters[1:]:
                if cluster.similar(other, self._cluster_threshold):
                    to_merge.append(other)
            if to_merge:
                self._merge_clusters([cluster] + to_merge)
                merged_any = True

    def _merge_clusters(self, clusters):
        merged = clusters[0]
        to_prune = clusters[1:]
        for c in to_prune:
            merged.add(c.centroid())
            for (x, y), cl in self.cluster_assignments.items():
                if cl == c:
                    self.cluster_assignments[(x, y)] = merged
        self.clusters = [c for c in self.clusters if c not in to_prune]
        merged.recalc_centroid()

    def _recalc_centroids(self):
        for c in self.clusters:
            c.recalc_centroid()

    def cluster(self, img):
        self._init_clusters(img)
        if len(self.clusters) < 2:
            return

        itercount = 0
        maxiters = self._max_iters
        thresh = 0.01

        while itercount < maxiters:
            orig_means = [c.centroid() for c in self.clusters]
            iteration = [self._colorspace.to_rgbcolor(*c.centroid()) for c in self.clusters]
            self.rounds.append(iteration)

            for x, y, components in ColorClusterer.each_img_color(img, self._colorspace):
                c = self._add_to_nearest(components)
                self.cluster_assignments[(x, y)] = c

            self._recalc_centroids()
            self._merge_similar()

            new_means = [c.centroid() for c in self.clusters]

            # If the clusters haven't changed much since the last round, we're done.
            if all(self._colorspace.distance(u[0], u[1], u[2], v[0], v[1], v[2]) < thresh for u, v in
                   zip(orig_means, new_means)):
                break

            itercount += 1


def output(imgpath, clusters, rounds, colorspace):
    s = "<!doctype html>"
    s += "\n<html>"
    s += '\n\t<head><style>div { margin: 1em; } #gradArt { width: 700px; height: 700px; }</style></head>'
    s += '\n\t<body>'
    s += f'\n\t\t<div><img src="file://{imgpath}"></div>'
    s += f'\n\t\t<div><img src="file:///tmp/cluster.jpg"></div>'

    def to_rgb_100(a):
        return round(a / 256.0 * 100, 2)

    for i, rgbs in enumerate(rounds):
        s += f"<div><h3>Round {i + 1}</h3>"
        for rgb in rgbs:
            r, g, b = rgb.to_100()
            s += f'\n\t\t<div style="background-color: rgb({r}%,{g}%,{b}%); min-height: 100px; width=100px; border: 1px solid black;"></div>'
        s += "</div>"

    for cluster in clusters:
        rgb = colorspace.to_rgbcolor(*cluster.centroid())
        r, g, b = rgb.to_100()
        s += f'\n\t\t<div style="background-color: rgb({r}%,{g}%,{b}%); min-height: 200px; width=100%; border: 1px solid black;">{cluster.label} <h1>Count: {cluster.count()}</h1> {str(cluster.dist_dict)}</div>'

    s += "<div id=\"gradArt\">"
    s += "</div>"
    s += '\n\t</body>'
    s += "\n</html>"
    with open("/tmp/clusters.html", 'w') as f:
        f.write(s)


def space_for(space):
    return RGBColorSpace if space == 'rgb' else HSVColorSpace


def clusterize(pixbuf, rng, maxedge=200, k=7, cluster_thresh=0.6, max_iters=200, space='hsv'):
    assert pixbuf.get_bits_per_sample() == 8
    assert pixbuf.get_colorspace() == GdkPixbuf.Colorspace.RGB

    if pixbuf.get_height() > maxedge and pixbuf.get_width() > maxedge:
        pixbuf = pixbuf.scale_simple(maxedge, maxedge, GdkPixbuf.InterpType.BILINEAR)

    img = Image(pixbuf)
    color_space = space_for(space)
    clusterer = ColorClusterer(k, cluster_thresh, rng, max_iters, color_space)
    clusterer.cluster(img)
    clusters = clusterer.clusters

    dist = color_space.distance
    white = Cluster('white', color_space.as_3_tuple(RGBColor(1, 1, 1)), triplet_mean, color_space)
    black = Cluster('black', color_space.as_3_tuple(RGBColor(0, 0, 0)), triplet_mean, color_space)
    bw_thresh = 0.0105

    def black_or_white(c):
        w = white.centroid()
        b = black.centroid()
        m = c.centroid()
        dw = color_space.distance(m[0], m[1], m[2], w[0], w[1], w[2])
        if dw < bw_thresh:
            return True
        db = color_space.distance(m[0], m[1], m[2], b[0], b[1], b[2])
        return db < bw_thresh

    clusters = [c for c in clusters if not black_or_white(c)]
    kept = set()
    l = len(clusters)

    for i in range(l):
        c = clusters[i]
        kept.add(c.label)
        for j in range(i + 1, l):
            d = clusters[j]
            if not c.similar(d):
                kept.add(d.label)

    return clusterer, img, sorted([c for c in clusters if c.label in kept], key=lambda c: c.count(),
                                  reverse=True), clusterer.rounds


class ClusteringResult:
    def __init__(self, clusters, colorspace):
        self.clusters = clusters
        self._color_space = colorspace

    def dominant(self):
        c = self._color_space.to_rgbcolor(*self.clusters[0].centroid())
        return c

    def complementary(self):
        choice = (random.choice(self.clusters))
        return self._color_space.to_rgbcolor(*choice.centroid())


def main(args):
    from PIL import Image
    import argparse
    import time

    parser = argparse.ArgumentParser(prog='cluster', description='Clusterize an image using k-means',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('file', help='jpg file path')
    parser.add_argument('-e', '--edge', help='edge_size', default=200, type=int)
    parser.add_argument('-k', '--k', help='number of clusters', default=7, type=int)
    parser.add_argument('-t', '--thresh', help='cluster distance threshold', default=0.001, type=float)
    parser.add_argument('-i', '--iters', help='max number of iterations', default=100, type=int)
    parser.add_argument('-s', '--space', help='color space for distance', choices=['rgb', 'hsv'], default='hsv')
    parsed = parser.parse_args(args)

    with open(parsed.file, 'rb') as f:
        pixbuf = pixbuf_from_file(f)

    rng = random.Random()
    rng.seed(int(1000 * time.time()))

    clusterer, pixbuf_img, clusters, rounds = \
        clusterize(pixbuf, rng, parsed.edge, parsed.k, parsed.thresh, parsed.iters, parsed.space)
    colorspace = space_for(parsed.space)
    for c in clusters:
        dist_dict = {}
        for d in clusters:
            if c is d:
                continue
            dist_dict[d.label] = colorspace.distance(
                c.centroid()[0], c.centroid()[1], c.centroid()[2],
                d.centroid()[0], d.centroid()[1], d.centroid()[2]
            )
        c.dist_dict = dist_dict

    im = Image.new('RGB', (parsed.edge, parsed.edge))

    for row in range(parsed.edge):
        for col in range(parsed.edge):
            clust = clusterer.cluster_assignments[(col, row)]
            a, b, c = clust.centroid()
            rgb = colorspace.to_rgb_256_tuple(a, b, c)
            im.putpixel((col, row), rgb)

    im.save('/tmp/cluster.jpg')
    output(parsed.file, clusters, rounds, colorspace)


if __name__ == '__main__':
    main(sys.argv[1:])
