# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# File Author: Marius Adrian Stanciu (c)                   #
# Date: 3/10/2019                                          #
# MIT Licence                                              #
# ##########################################################

from shapely.geometry import LineString
from shapely.affinity import rotate
from ezdxf.math import Vector as ezdxf_vector

from appParsers.ParseFont import *
from appParsers.ParseDXF_Spline import *
import logging

log = logging.getLogger('base2')


def distance(pt1, pt2):
    return math.sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)


def dxfpoint2shapely(point):

    geo = Point(point.dxf.location).buffer(0.01)
    return geo


def dxfline2shapely(line):

    try:
        start = (line.dxf.start[0], line.dxf.start[1])
        stop = (line.dxf.end[0], line.dxf.end[1])

    except Exception as e:
        log.debug(str(e))
        return None

    geo = LineString([start, stop])

    return geo


def dxfcircle2shapely(circle, n_points=100):

    ocs = circle.ocs()
    # if the extrusion attribute is not (0, 0, 1) then we have to change the coordinate system from OCS to WCS
    if circle.dxf.extrusion != (0, 0, 1):
        center_pt = ocs.to_wcs(circle.dxf.center)
    else:
        center_pt = circle.dxf.center

    radius = circle.dxf.radius
    geo = Point(center_pt).buffer(radius, int(n_points / 4))

    return geo


def dxfarc2shapely(arc, n_points=100):
    # ocs = arc.ocs()
    # # if the extrusion attribute is not (0, 0, 1) then we have to change the coordinate system from OCS to WCS
    # if arc.dxf.extrusion != (0, 0, 1):
    #     arc_center = ocs.to_wcs(arc.dxf.center)
    #     start_angle = math.radians(arc.dxf.start_angle) + math.pi
    #     end_angle = math.radians(arc.dxf.end_angle) + math.pi
    #     dir = 'CW'
    # else:
    #     arc_center = arc.dxf.center
    #     start_angle = math.radians(arc.dxf.start_angle)
    #     end_angle = math.radians(arc.dxf.end_angle)
    #     dir = 'CCW'
    #
    # center_x = arc_center[0]
    # center_y = arc_center[1]
    # radius = arc.dxf.radius
    #
    # point_list = []
    #
    # if start_angle > end_angle:
    #     start_angle +=  2 * math.pi
    #
    # line_seg = int((n_points * (end_angle - start_angle)) / math.pi)
    # step_angle = (end_angle - start_angle) / float(line_seg)
    #
    # angle = start_angle
    # for step in range(line_seg + 1):
    #     if dir == 'CCW':
    #         x = center_x + radius * math.cos(angle)
    #         y = center_y + radius * math.sin(angle)
    #     else:
    #         x = center_x + radius * math.cos(-angle)
    #         y = center_y + radius * math.sin(-angle)
    #     point_list.append((x, y))
    #     angle += step_angle
    #
    #
    # log.debug("X = %.4f, Y = %.4f, Radius = %.4f, start_angle = %.1f, stop_angle = %.1f, step_angle = %.4f, dir=%s" %
    #           (center_x, center_y, radius, start_angle, end_angle, step_angle, dir))
    #
    # geo = LineString(point_list)
    # return geo

    ocs = arc.ocs()
    # if the extrusion attribute is not (0, 0, 1) then we have to change the coordinate system from OCS to WCS
    if arc.dxf.extrusion != (0, 0, 1):
        arc_center = ocs.to_wcs(arc.dxf.center)
        start_angle = arc.dxf.start_angle + 180
        end_angle = arc.dxf.end_angle + 180
        direction = 'CW'
    else:
        arc_center = arc.dxf.center
        start_angle = arc.dxf.start_angle
        end_angle = arc.dxf.end_angle
        direction = 'CCW'

    center_x = arc_center[0]
    center_y = arc_center[1]
    radius = arc.dxf.radius

    point_list = []

    if start_angle > end_angle:
        start_angle = start_angle - 360
    angle = start_angle

    step_angle = float(abs(end_angle - start_angle) / n_points)

    while angle <= end_angle:
        if direction == 'CCW':
            x = center_x + radius * math.cos(math.radians(angle))
            y = center_y + radius * math.sin(math.radians(angle))
        else:
            x = center_x + radius * math.cos(math.radians(-angle))
            y = center_y + radius * math.sin(math.radians(-angle))
        point_list.append((x, y))
        angle += abs(step_angle)

    # in case the number of segments do not cover everything until the end of the arc
    if angle != end_angle:
        if direction == 'CCW':
            x = center_x + radius * math.cos(math.radians(end_angle))
            y = center_y + radius * math.sin(math.radians(end_angle))
        else:
            x = center_x + radius * math.cos(math.radians(- end_angle))
            y = center_y + radius * math.sin(math.radians(- end_angle))
        point_list.append((x, y))

    # log.debug("X = %.4f, Y = %.4f, Radius = %.4f, start_angle = %.1f, stop_angle = %.1f, step_angle = %.4f" %
    #           (center_x, center_y, radius, start_angle, end_angle, step_angle))

    geo = LineString(point_list)
    return geo


def dxfellipse2shapely(ellipse, ellipse_segments=100):
    # center = ellipse.dxf.center
    # start_angle = ellipse.dxf.start_param
    # end_angle = ellipse.dxf.end_param

    ocs = ellipse.ocs()
    # if the extrusion attribute is not (0, 0, 1) then we have to change the coordinate system from OCS to WCS
    if ellipse.dxf.extrusion != (0, 0, 1):
        center = ocs.to_wcs(ellipse.dxf.center)
        start_angle = ocs.to_wcs(ellipse.dxf.start_param)
        end_angle = ocs.to_wcs(ellipse.dxf.end_param)
        direction = 'CW'
    else:
        center = ellipse.dxf.center
        start_angle = ellipse.dxf.start_param
        end_angle = ellipse.dxf.end_param
        direction = 'CCW'

    # print("Dir = %s" % dir)
    major_axis = ellipse.dxf.major_axis
    ratio = ellipse.dxf.ratio

    points_list = []
    major_axis = Vector(list(major_axis))

    major_x = major_axis[0]
    major_y = major_axis[1]

    if start_angle >= end_angle:
        end_angle += 2.0 * math.pi

    line_seg = int((ellipse_segments * (end_angle - start_angle)) / math.pi)
    step_angle = abs(end_angle - start_angle) / float(line_seg)

    angle = start_angle
    for step in range(line_seg + 1):
        if direction == 'CW':
            major_dim = normalize_2(major_axis)
            minor_dim = normalize_2(Vector([ratio * k for k in major_axis]))
            vx = (major_dim[0] + major_dim[1]) * math.cos(angle)
            vy = (minor_dim[0] - minor_dim[1]) * math.sin(angle)
            x = center[0] + major_x * vx - major_y * vy
            y = center[1] + major_y * vx + major_x * vy
            angle += step_angle
        else:
            major_dim = normalize_2(major_axis)
            minor_dim = (Vector([ratio * k for k in major_dim]))
            vx = (major_dim[0] + major_dim[1]) * math.cos(angle)
            vy = (minor_dim[0] + minor_dim[1]) * math.sin(angle)
            x = center[0] + major_x * vx + major_y * vy
            y = center[1] + major_y * vx + major_x * vy
            angle += step_angle

        points_list.append((x, y))

    geo = LineString(points_list)
    return geo


def dxfpolyline2shapely(polyline):
    final_pts = []
    pts = polyline.points()
    for i in pts:
        final_pts.append((i[0], i[1]))
    if polyline.is_closed:
        final_pts.append(final_pts[0])

    geo = LineString(final_pts)
    return geo


def dxflwpolyline2shapely(lwpolyline):
    final_pts = []

    for point in lwpolyline:
        x, y, _, _, _ = point
        final_pts.append((x, y))
    if lwpolyline.closed:
        final_pts.append(final_pts[0])

    geo = LineString(final_pts)
    return geo


def dxfsolid2shapely(solid):
    iterator = 0
    corner_list = []
    try:
        corner_list.append(solid[iterator])
        iterator += 1
    except Exception:
        return Polygon(corner_list)


def dxfspline2shapely(spline):
    # for old version of ezdxf
    # with spline.edit_data() as spline_data:
    #     ctrl_points = spline_data.control_points
    #     try:
    #         # required if using old version of ezdxf
    #         knot_values = spline_data.knot_values
    #     except AttributeError:
    #         knot_values = spline_data.knots

    ctrl_points = spline.control_points
    knot_values = spline.knots
    is_closed = spline.closed
    degree = spline.dxf.degree

    x_list, y_list, _ = spline2Polyline(ctrl_points, degree=degree, closed=is_closed, segments=20, knots=knot_values)
    points_list = zip(x_list, y_list)

    geo = LineString(points_list)
    return geo


def dxftrace2shapely(trace):
    iterator = 0
    corner_list = []
    try:
        corner_list.append(trace[iterator])
        iterator += 1
    except Exception:
        return Polygon(corner_list)


def getdxfgeo(dxf_object):

    msp = dxf_object.modelspace()
    geos = get_geo(dxf_object, msp)

    # geo_block = get_geo_from_block(dxf_object)

    return geos


def get_geo_from_insert(dxf_object, insert):
    geo_block_transformed = []

    phi = insert.dxf.rotation
    tr = insert.dxf.insert
    sx = insert.dxf.xscale
    sy = insert.dxf.yscale
    r_count = insert.dxf.row_count
    r_spacing = insert.dxf.row_spacing
    c_count = insert.dxf.column_count
    c_spacing = insert.dxf.column_spacing

    # print(phi, tr)

    # identify the block given the 'INSERT' type entity name
    block = dxf_object.blocks[insert.dxf.name]
    block_coords = (block.block.dxf.base_point[0], block.block.dxf.base_point[1])

    # get a list of geometries found in the block
    geo_block = get_geo(dxf_object, block)

    # iterate over the geometries found and apply any transformation found in the 'INSERT' entity attributes
    for geo in geo_block:

        # get the bounds of the geometry
        # minx, miny, maxx, maxy = geo.bounds

        if tr[0] != 0 or tr[1] != 0:
            geo = translate(geo, (tr[0] - block_coords[0]), (tr[1] - block_coords[1]))

        # support for array block insertions
        if r_count > 1:
            for r in range(r_count):
                geo_block_transformed.append(translate(geo, (tr[0] + (r * r_spacing) - block_coords[0]), 0))
        if c_count > 1:
            for c in range(c_count):
                geo_block_transformed.append(translate(geo, 0, (tr[1] + (c * c_spacing) - block_coords[1])))

        if sx != 1 or sy != 1:
            geo = scale(geo, sx, sy)
        if phi != 0:
            if isinstance(tr, str) and tr.lower() == 'c':
                tr = 'center'
            elif isinstance(tr, ezdxf_vector):
                tr = list(tr)
            geo = rotate(geo, phi, origin=tr)

        geo_block_transformed.append(geo)
    return geo_block_transformed


def get_geo(dxf_object, container):
    # store shapely geometry here
    geo = []

    for dxf_entity in container:
        g = []
        # print("Entity", dxf_entity.dxftype())
        if dxf_entity.dxftype() == 'POINT':
            g = dxfpoint2shapely(dxf_entity,)
        elif dxf_entity.dxftype() == 'LINE':
            g = dxfline2shapely(dxf_entity,)
        elif dxf_entity.dxftype() == 'CIRCLE':
            g = dxfcircle2shapely(dxf_entity)
        elif dxf_entity.dxftype() == 'ARC':
            g = dxfarc2shapely(dxf_entity)
        elif dxf_entity.dxftype() == 'ELLIPSE':
            g = dxfellipse2shapely(dxf_entity)
        elif dxf_entity.dxftype() == 'LWPOLYLINE':
            g = dxflwpolyline2shapely(dxf_entity)
        elif dxf_entity.dxftype() == 'POLYLINE':
            g = dxfpolyline2shapely(dxf_entity)
        elif dxf_entity.dxftype() == 'SOLID':
            g = dxfsolid2shapely(dxf_entity)
        elif dxf_entity.dxftype() == 'TRACE':
            g = dxftrace2shapely(dxf_entity)
        elif dxf_entity.dxftype() == 'SPLINE':
            g = dxfspline2shapely(dxf_entity)
        elif dxf_entity.dxftype() == 'INSERT':
            g = get_geo_from_insert(dxf_object, dxf_entity)
        else:
            log.debug(" %s is not supported yet." % dxf_entity.dxftype())

        if g is not None:
            if type(g) == list:
                for subg in g:
                    geo.append(subg)
            else:
                geo.append(g)

    return geo


def getdxftext(exf_object, object_type, units=None):
    pass

# def get_geo_from_block(dxf_object):
#     geo_block_transformed = []
#
#     msp = dxf_object.modelspace()
#     # iterate through all 'INSERT' entities found in modelspace msp
#     for insert in msp.query('INSERT'):
#         phi = insert.dxf.rotation
#         tr = insert.dxf.insert
#         sx = insert.dxf.xscale
#         sy = insert.dxf.yscale
#         r_count = insert.dxf.row_count
#         r_spacing = insert.dxf.row_spacing
#         c_count = insert.dxf.column_count
#         c_spacing = insert.dxf.column_spacing
#
#         # print(phi, tr)
#
#         # identify the block given the 'INSERT' type entity name
#         print(insert.dxf.name)
#         block = dxf_object.blocks[insert.dxf.name]
#         block_coords = (block.block.dxf.base_point[0], block.block.dxf.base_point[1])
#
#         # get a list of geometries found in the block
#         # store shapely geometry here
#         geo_block = []
#
#         for dxf_entity in block:
#             g = []
#             # print("Entity", dxf_entity.dxftype())
#             if dxf_entity.dxftype() == 'POINT':
#                 g = dxfpoint2shapely(dxf_entity, )
#             elif dxf_entity.dxftype() == 'LINE':
#                 g = dxfline2shapely(dxf_entity, )
#             elif dxf_entity.dxftype() == 'CIRCLE':
#                 g = dxfcircle2shapely(dxf_entity)
#             elif dxf_entity.dxftype() == 'ARC':
#                 g = dxfarc2shapely(dxf_entity)
#             elif dxf_entity.dxftype() == 'ELLIPSE':
#                 g = dxfellipse2shapely(dxf_entity)
#             elif dxf_entity.dxftype() == 'LWPOLYLINE':
#                 g = dxflwpolyline2shapely(dxf_entity)
#             elif dxf_entity.dxftype() == 'POLYLINE':
#                 g = dxfpolyline2shapely(dxf_entity)
#             elif dxf_entity.dxftype() == 'SOLID':
#                 g = dxfsolid2shapely(dxf_entity)
#             elif dxf_entity.dxftype() == 'TRACE':
#                 g = dxftrace2shapely(dxf_entity)
#             elif dxf_entity.dxftype() == 'SPLINE':
#                 g = dxfspline2shapely(dxf_entity)
#             elif dxf_entity.dxftype() == 'INSERT':
#                 log.debug("Not supported yet.")
#             else:
#                 log.debug("Not supported yet.")
#
#             if g is not None:
#                 if type(g) == list:
#                     for subg in g:
#                         geo_block.append(subg)
#                 else:
#                     geo_block.append(g)
#
#         # iterate over the geometries found and apply any transformation found in the 'INSERT' entity attributes
#         for geo in geo_block:
#             if tr[0] != 0 or tr[1] != 0:
#                 geo = translate(geo, (tr[0] - block_coords[0]), (tr[1] - block_coords[1]))
#
#             # support for array block insertions
#             if r_count > 1:
#                 for r in range(r_count):
#                     geo_block_transformed.append(translate(geo, (tr[0] + (r * r_spacing) - block_coords[0]), 0))
#
#             if c_count > 1:
#                 for c in range(c_count):
#                     geo_block_transformed.append(translate(geo, 0, (tr[1] + (c * c_spacing) - block_coords[1])))
#
#             if sx != 1 or sy != 1:
#                 geo = scale(geo, sx, sy)
#             if phi != 0:
#                 geo = rotate(geo, phi, origin=tr)
#
#             geo_block_transformed.append(geo)
#     return geo_block_transformed
