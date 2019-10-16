# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""
Functions used to render the objets into polygons, hfss and so on.

@date: 2019
@author: Zlatko K. Minev
"""

import pyEPR
import ast
import numpy as np

from numpy import sqrt, pi, array, flip
from numpy.linalg import norm
from collections import namedtuple
from pyEPR.toolbox import combinekw
from shapely.geometry import CAP_STYLE, JOIN_STYLE

from . import Dict
from .draw_utility import to_Vec3D, parse_units, get_vec_unit_norm, \
    TRUE_STR, unparse_units, unit_vector,\
    parse_options_hfss, Point, LineString, buffer,\
    array_chop
from .draw_utility import *
from . import draw_hfss
from .config import DEFAULT, DEFAULT_OPTIONS

_angle_Y2X = {'X':-90,'Y':0} # If draw along the Y axis, takes Y axis to X. Keeps Y fixed.


################################################################################
###
# Universal core drawing func properties
###

# @deprecated
def do_PerfE(options, circ, obj):
    _, oModeler = circ.get_modeler()
    if options.get('do_PerfE',  DEFAULT['do_PerfE']):
        oModeler.append_PerfE_assignment(
            str(obj) if options.get('BC_individual', DEFAULT['BC_individual'])
            else options.get('BC_name', 'PerfE'), [str(obj)])


# @deprecated
def do_cut_ground(options, circ, objs):
    ''' do_cut '''
    _, oModeler = circ.get_modeler()
    if options.get('do_cut',  DEFAULT['do_cut']):
        assert isinstance(objs, list)
        oModeler.subtract(circ.get_ground_plane(options), objs)

# @deprecated


def do_mesh(options, circ, objs):
    ''' do_mesh  - TO DO replace with funciton draw_hfss'''
    _, oModeler = circ.get_modeler()
    if options.get('do_mesh',  DEFAULT._hfss.do_mesh):
        assert isinstance(objs, list)
        oModeler.subtract(circ.get_ground_plane(options), objs)


################################################################################
###
# Susbtrate and bounding box
###

# Absolute Offset for -+X, -+Y, and -+Z; # 890 is the nominal depth of the copper penny 35 mil
DEFAULT_OPTIONS['draw_bounding_box'] = [[0, 0], [0, 0], ['0.890mm', '0.900mm']],


def draw_bounding_box(circ, options=DEFAULT_OPTIONS['draw_bounding_box']):
    """
    .. figure:: figures/draw_chip1.png
        :align: center
        :width: 6in
    """
    _, oModeler = circ.get_modeler()

    oModeler.draw_region(options, PaddingType="Absolute Offset")


# draw_substrate
 # For chip size, negative draws the substrate box down
DEFAULT_OPTIONS['draw_substrate'] = Dict({
    'pos_xy': ['0um', '0um'],
    'size': ['8.5mm', '6.5mm', '-0.750mm'],
    'elevation': 0,
    'ground_plane': 'ground_plane',
    'substrate': 'substrate',
    'material': 'cold silicon',
    'color_plane': DEFAULT.colors.ground_main,
    'transparency_plane': 0,
    'transparency_substrate': 0,
    'wireframe_substrate': False
})


def draw_substrate(circ, options):
    """
    .. figure:: figures/draw_chip1.png
        :align: center
        :width: 6in

    Args:
        elevation: Specify the z heigth
    """
    options = {**DEFAULT_OPTIONS['draw_substrate'], **options}
    _, oModeler = circ.get_modeler()

    elevation, size, pos_xy = parse_options_hfss(options, ['elevation', 'size', 'pos_xy'])
    origin = array([*pos_xy, elevation])

    # sheet
    oModeler.draw_rect_center(origin,
                              size[0], size[1], 0,
                              name=options['ground_plane'],
                              color=options['color_plane'],
                              transparency=options['transparency_plane'])
    oModeler.assign_perfect_E(options['ground_plane'],
                              name=options['ground_plane'])

    # substrate box
    oModeler.draw_box_corner([origin[0]-size[0]/2., origin[1]-size[1]/2, origin[2]],
                             size,
                             name=options['substrate'],
                             material=options['material'],
                             color=(186, 186, 205),
                             transparency=options['transparency_substrate'],
                             wireframe=options['wireframe_substrate'])


####################################################################################
###
# Connector - This should move and be a class TODO: Make a class and move to planar circuit
###


def make_connector_props(points, options,
                         orient=[+1, +1],
                         vec_normal=None,
                         unparse=False):
    '''
    ASSUMED HFSS UNITS as INPUT PUTS TO NON-HFSS UNTIS

    Makes a connector dictionary with required prpoerties givent two
    points, assumed to be the mating  edge.

    Assumed the input points are parsed_units and come in 90 deg pattern

    #TODO: Perhaps make into a class. Then can check for class
    '''
    assert len(points) == 2
    unparse_units1 = unparse_units if unparse else lambda x: x

    vec_D, vec_d, vec_n = get_vec_unit_norm(points)
    _orient = 'orient' if 'orient' in options else 'orientation'

    if not vec_normal is None:
        vec_normal = array_chop(vec_normal)
        #from . import logger
        # logger.info(f'vec_normal1={vec_normal}')
        vec_n = unit_vector(vec_normal)  # overide

    else:
        vec_n = (orient[0]*orient[1]*vec_n)*(
            -1 if options.get(_orient, 'x'.lower()) == 'x'
            else +1)
    #TODO: Handle 3 and 2 vectors
    return Dict({
                'pos': unparse_units1(np.sum(points, axis=0)/2.),
                'normal': vec_n,
                'tangent': vec_d,
                'width': unparse_units1(norm(vec_D)),
                'chip': options.get('chip', 'main'),
                'points': points,
                })