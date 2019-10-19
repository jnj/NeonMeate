import argparse
import sys

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import cv2

import numpy as np


def create_arg_parser():
    p = argparse.ArgumentParser(
        prog='dominant',
        description='Store dominant color information in jpeg files',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument('file')
    return p


def main(args):
    arg_parser = create_arg_parser()
    parsed = arg_parser.parse_args(args)
    imgpath = parsed.file
    img = cv2.imread(imgpath)

    num_quant_levels = 8
    indices = np.arange(0, 256)
    divider = np.linspace(0, 255, num_quant_levels + 1)[1]
    quantiz = np.int0(np.linspace(0, 255, num_quant_levels))
    color_levels = np.clip(np.int0(indices / divider), 0, num_quant_levels - 1)
    palette = quantiz[color_levels]
    im2 = palette[img]
    im2 = cv2.convertScaleAbs(im2)

    cv2.imshow('im2', im2)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    # r, g, b = cv2.split(img)
    # r = r.flatten()
    # g = g.flatten()
    # b = b.flatten()
    #
    # fig = plt.figure()
    # ax = Axes3D(fig)
    # ax.scatter(r, g, b)
    # plt.show()


if __name__ == '__main__':
    main(sys.argv[1:])
