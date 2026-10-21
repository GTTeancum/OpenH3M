"""World-coordinate interpretation of the user's 2026-10-21 red-line sketch.

This planning boundary is not collision containment. Full visual geometry stays
in both maps. The Gulch side includes the canyon and Montana/coastline, while
the island, beach cave and distant waterfall stay on the World side.
"""
import numpy as np

# (source X, source Y). Gulch lies at Y <= boundary(X). Endpoints extend beyond
# the source world bounds. Corners follow the mouth rather than a rectangular cut.
BOUNDARY = ((-250., 10.), (-110., 10.), (-80., 5.), (-55., -5.),
            (-35., -20.), (-10., -45.), (25., -55.),
            (100., -55.), (320., -65.))


def boundary_y(x):
    points = np.asarray(BOUNDARY)
    return np.interp(x, points[:, 0], points[:, 1])


def classify_bounds(mins, maxs):
    """Conservative inclusion; retain crossing polygons intact on both sides.

    Evaluate every polyline corner inside each surface's X range. This avoids
    losing polygons that cross a bend even if all their vertices lie to one side.
    Bounding-box false positives are acceptable; omitted collision is not.
    """
    mins, maxs = np.asarray(mins), np.asarray(maxs)
    low = np.minimum(boundary_y(mins[:, 0]), boundary_y(maxs[:, 0]))
    high = np.maximum(boundary_y(mins[:, 0]), boundary_y(maxs[:, 0]))
    for x, y in BOUNDARY:
        inside = (mins[:, 0] <= x) & (maxs[:, 0] >= x)
        low = np.where(inside, np.minimum(low, y), low)
        high = np.where(inside, np.maximum(high, y), high)
    return mins[:, 1] <= high, maxs[:, 1] >= low
