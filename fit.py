#!/usr/bin/env python3
import os
import sys

import numpy as np
import pints
from scipy.optimize import shgo

import nevis

# Load height data, create (or load cached) spline
nevis.howdy('Local')
nevis.gb(9 if '-debug' in sys.argv else None)
#f = nevis.spline()
f = nevis.linear_interpolant()


def pints_method():
    """
    Fit using ``pints.OptimisationController``.
    """
    # Visited points, and means per iteration
    points = []
    trajectory = []

    # Use best found, instead of best guessed
    x_best = False

    # Create pints error measure

    class Error(pints.ErrorMeasure):
        """
        Turn a height into an error to be minimised.

        Writes to global var: not suitable for parallelistion!
        """

        def __init__(self, spline):
            self.f = spline

        def n_parameters(self):
            return 2

        def __call__(self, p):
            points.append(p)
            return -self.f(*p)

    # Create callback to store means
    def cb(i, opt):
        trajectory.append(opt.x_best() if x_best else opt.x_guessed())
    # Create pints boundaries
    w, h = nevis.dimensions()
    b = pints.RectangularBoundaries([0, 0], [w, h])
    #
    # Run!
    #
    e = Error(f)
    x0 = b.sample()
    s0 = min(b.range()) / 2
    opt = pints.OptimisationController(
        e,
        x0=x0,
        sigma0=s0,
        boundaries=b,
        method=pints.CMAES
    )
    opt.optimiser().set_population_size(100)
    opt.set_callback(cb)
    opt.set_max_unchanged_iterations(100, threshold=0.01)
    opt.set_f_guessed_tracking(not x_best)
    (x, y), z = opt.run()

    # Get final result and some comparison points
    return x, y, z, points, trajectory


def shgo_method():
    """
    Fit using ``scipy.optimize.shgo``.
    """
    # Visited points, and means per iteration
    points = []

    # Data boundaries
    w, h = nevis.dimensions()

    # Callback at each step
    def cb(xk):
        points.append(xk)
    #
    # Run!
    #
    result = shgo(
        func=lambda t: -f(*t),
        bounds=((0, w), (0, h)),
        callback=cb,
    )
    x, y = result.x
    z = result.fun
    trajectory = result.xl
    print(result.message)

    return x, y, z, points, trajectory


def plot_results(x, y, z, points, trajectory):
    """
    Plot the results of a fitting model.
    """

    z = -int(round(float(z)))
    c = nevis.Coords(gridx=x, gridy=y)
    h, d = nevis.Hill.nearest(c)

    # Visited points
    points = np.array(points)
    trajectory = np.array(trajectory)

    # Ensure results directory exists
    root = 'results'
    if not os.path.isdir(root):
        os.makedirs(root)

    #
    # Figure 1: Full map
    #
    downsampling = 3 if '-debug' in sys.argv else 27
    labels = {
        'Ben Nevis': nevis.ben(),
        h.name: h.coords,
        'You': c,
    }
    fig, ax, data, g = nevis.plot(
        labels=labels,
        trajectory=trajectory,
        points=points,
        downsampling=downsampling,
        silent=True)
    path = os.path.join(root, 'local-map-full.png')
    print()
    print(f'Saving figure to {path}.')
    fig.savefig(path)

    #
    # Figure 2: Zoomed map
    #
    b = 20e3
    boundaries = [x - b, x + b, y - b, y + b]
    downsampling = 1
    labels = {
        'Ben Nevis': nevis.ben(),
        h.name: h.coords,
        'You': c,
    }
    fig, ax, data, g = nevis.plot(
        boundaries=boundaries,
        labels=labels,
        trajectory=trajectory,
        points=points,
        downsampling=downsampling,
        silent=True)
    path = os.path.join(root, 'local-map-zoom.png')
    print(f'Saving figure to {path}.')
    fig.savefig(path)

    #
    # Figure 3: Line from known top to you
    #
    fig, ax, p1, p2 = nevis.plot_line(f, c, h.coords, 'You', h.name)
    path = os.path.join(root, 'local-line-plot.png')
    print(f'Saving figure to {path}.')
    fig.savefig(path)

    #
    # Print results
    #
    print()
    print('Congratulations!' if d < 100 else (
        'Good job!' if d < 1000 else 'Interesting!'))
    print(f'You landed at an altitude of {z}m.')
    print(f'  {c.opentopomap}')

    dm = f'{round(d)}m' if d < 1000 else f'{round(d / 1000, 1)}km'
    print(f'You are {dm} from the nearest named hill top, "{h.name}",')
    print(f'  ranked the {h.ranked} heighest in GB.')
    p = h.photo()
    if p:
        print('  ' + p)
    print()


# plot_results(*pints_method())
plot_results(*shgo_method())
