"""
Implementation of gaussian filter algorithm
"""

from itertools import product

from cv2 import COLOR_BGR2GRAY, cvtColor, imread, imshow, waitKey
from numpy import dot, exp, mgrid, pi, ravel, square, uint8, zeros


def gen_gaussian_kernel(ksize, sigma):
    center = ksize // 2
    x, y = mgrid[0 - center : ksize - center, 0 - center : ksize - center]
    g = 1 / (2 * pi * sigma) * exp(-(square(x) + square(y)) / (2 * square(sigma)))
    return g


def gaussian_filter(image, ksize, sigma):
    height, width = image.shape[0], image.shape[1]
    # dst image height and width
    dst_height = height - ksize + 1;
    dst_width = width - ksize + 1

    # im2col, turn the ksize*ksize pixels into a row and np.vstack all rows
    image_array = zeros((dst_height * dst_width, ksize * ksize))
    for row, (i, j) in enumerate(product(range(dst_height), range(dst_width))):
        window = ravel(image[i : i + ksize, j : j + ksize])
        image_array[row, :] = window

    #  turn the kernel into shape(k*k, 1)
    gaussian_kernel = gen_gaussian_kernel(ksize, sigma)
    filter_array = ravel(gaussian_kernel)

    # reshape and get the dst image
    dst = dot(image_array, filter_array).reshape(dst_height, dst_width).astype(uint8)

    return dst


if __name__ == "__main__":
    # read original image
    img = imread(r"../image_data/lena.jpg")
    # turn image in gray scale value
    gray = cvtColor(img, COLOR_BGR2GRAY)

    # get values with two different mask size
    gaussian3x3 = gaussian_filter(gray, 3, sigma=1)
    gaussian5x5 = gaussian_filter(gray, 5, sigma=0.8)

    # show result images
    imshow("gaussian filter with 3x3 mask", gaussian3x3)
    imshow("gaussian filter with 5x5 mask", gaussian5x5)
    waitKey()