# -*- coding: utf-8 -*-

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load RandomPoints class from file RandomPoints.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .random_points import RandomPoints
    return RandomPoints(iface)