# Copyright (c) 2024 - for information on the respective copyright owner
# see the NOTICE file

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.from typing import List

"""Expand expressions into jani."""

from math import pi
from typing import Dict

from jani_generator.jani_entries import JaniConstant, JaniExpression
from jani_generator.jani_entries.jani_expression_generator import (
    abs_operator, and_operator, divide_operator, equal_operator,
    floor_operator, greater_equal_operator, if_operator, lower_operator,
    max_operator, min_operator, minus_operator, modulo_operator,
    multiply_operator, or_operator, plus_operator, pow_operator)

BASIC_EXPRESSIONS_MAPPING = {
    "-": "-",
    "+": "+",
    "*": "*",
    "/": "/",
    "%": "%",
    "pow": "pow",
    "log": "log",
    "max": "max",
    "min": "min",
    "abs": "abs",
    ">": ">",
    "≥": "≥",
    ">=": "≥",
    "<": "<",
    "≤": "≤",
    "<=": "≤",
    "=": "=",
    "≠": "≠",
    "!=": "≠",
    "!": "¬",
    "¬": "¬",
    "sin": "sin",
    "cos": "cos",
    "floor": "floor",
    "ceil": "ceil",
    "∧": "∧",
    "&&": "∧",
    "and": "∧",
    "||": "∨",
    "ite": "ite",
    "⇒": "⇒",
    "=>": "⇒",
}


# Custom operators (CONVINCE, specific to mobile 2D robot use case)
def intersection_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "intersect", "robot": JaniExpression(left), "barrier": JaniExpression(right)})


def distance_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "distance", "robot": JaniExpression(left), "barrier": JaniExpression(right)})


def distance_to_point_operator(robot, target_x, target_y) -> JaniExpression:
    return JaniExpression({"op": "distance_to_point", "robot": JaniExpression(robot), "x": JaniExpression(target_x), "y": JaniExpression(target_y)})


def norm2d_operator(x=None, y=None, *, exp=None) -> JaniExpression:
    # Compute the norm of a 2D vector
    if exp is not None:
        assert exp.op == "norm2d"
        exp_x = exp.operands["x"]
        exp_y = exp.operands["y"]
    else:
        exp_x = x
        exp_y = y
    assert exp_x is not None and exp_y is not None, "The 2D vector components must be provided"
    sq_x_exp = multiply_operator(exp_x, exp_x)
    sq_y_exp = multiply_operator(exp_y, exp_y)
    sq_dist_exp = plus_operator(sq_x_exp, sq_y_exp)
    return pow_operator(sq_dist_exp, 0.5)


def cross2d_operator(x1=None, y1=None, x2=None, y2=None, *, exp=None) -> JaniExpression:
    # Compute the cross product of two 2D vectors
    if exp is not None:
        assert exp.op == "cross2d"
        exp_x1 = exp.operands["x1"]
        exp_y1 = exp.operands["y1"]
        exp_x2 = exp.operands["x2"]
        exp_y2 = exp.operands["y2"]
    else:
        exp_x1 = x1
        exp_y1 = y1
        exp_x2 = x2
        exp_y2 = y2
    assert exp_x1 is not None and exp_y1 is not None and exp_x2 is not None and exp_y2 is not None, "The 2D vectors components must be provided"
    return minus_operator(multiply_operator(exp_x1, exp_y2), multiply_operator(exp_y1, exp_x2))


def dot2d_operator(x1=None, y1=None, x2=None, y2=None, *, exp=None) -> JaniExpression:
    # Compute the dot product of two 2D vectors
    if exp is not None:
        assert exp.op == "cross2d"
        exp_x1 = exp.operands["x1"]
        exp_y1 = exp.operands["y1"]
        exp_x2 = exp.operands["x2"]
        exp_y2 = exp.operands["y2"]
    else:
        exp_x1 = x1
        exp_y1 = y1
        exp_x2 = x2
        exp_y2 = y2
    assert exp_x1 is not None and exp_y1 is not None and exp_x2 is not None and exp_y2 is not None, "The 2D vectors components must be provided"
    return plus_operator(multiply_operator(exp_x1, exp_x2), multiply_operator(exp_y1, exp_y2))


def round_operator(value=None, *, exp=None) -> JaniExpression:
    if exp is not None:
        assert exp.op == "round"
        exp_value = exp.operands["exp"]
    else:
        exp_value = value
    assert exp_value is not None, "The value to round must be provided"
    return floor_operator(plus_operator(exp_value, 0.5))


def to_cm_operator(value=None, *, exp=None) -> JaniExpression:
    if exp is not None:
        assert exp.op == "to_cm"
        exp_value = exp.operands["exp"]
    else:
        exp_value = value
    assert exp_value is not None, "The value to convert in cm must be provided"
    return round_operator(multiply_operator(exp_value, 100.0))


def to_m_operator(value=None, *, exp=None) -> JaniExpression:
    if exp is not None:
        assert exp.op == "to_m"
        exp_value = exp.operands["exp"]
    else:
        exp_value = value
    assert exp_value is not None, "The value to convert in meters must be provided"
    return multiply_operator(exp_value, 0.01)


def to_deg_operator(value=None, *, exp=None) -> JaniExpression:
    if exp is not None:
        assert exp.op == "to_deg"
        exp_value = exp.operands["exp"]
    else:
        exp_value = value
    assert exp_value is not None, "The value to convert in degrees must be provided"
    # TODO: Use jani constants instead of the numeric PI value
    deg_val = round_operator(multiply_operator(exp_value, 180.0 / pi))
    return modulo_operator(deg_val, 360)


def to_rad_operator(value=None, *, exp=None) -> JaniExpression:
    if exp is not None:
        assert exp.op == "to_rad"
        exp_value = exp.operands["exp"]
    else:
        exp_value = value
    assert exp_value is not None, "The value to convert in radians must be provided"
    return multiply_operator(exp_value, pi / 180.0)


# Functionalities for interpolation
def __expression_interpolation_single_boundary(jani_constants: Dict[str, JaniConstant], robot_name: str, boundary_id: int) -> JaniExpression:
    n_vertices = jani_constants["boundaries.count"].value()
    # Variables names
    robot_radius = f"robots.{robot_name}.shape.radius"
    s_x = f"robots.{robot_name}.pose.x"
    s_y = f"robots.{robot_name}.pose.y"
    e_x = f"robots.{robot_name}.goal.x"
    e_y = f"robots.{robot_name}.goal.y"
    a_x = f"boundaries.{boundary_id}.x"
    a_y = f"boundaries.{boundary_id}.y"
    b_x = f"boundaries.{(boundary_id + 1) % n_vertices}.x"
    b_y = f"boundaries.{(boundary_id + 1) % n_vertices}.y"
    # Segments expressions
    ab_x = minus_operator(b_x, a_x)
    ab_y = minus_operator(b_y, a_y)
    ba_x = minus_operator(a_x, b_x)
    ba_y = minus_operator(a_y, b_y)
    ea_x = minus_operator(a_x, e_x)
    ea_y = minus_operator(a_y, e_y)
    eb_x = minus_operator(b_x, e_x)
    eb_y = minus_operator(b_y, e_y)
    es_x = minus_operator(s_x, e_x)
    es_y = minus_operator(s_y, e_y)
    # All other expressions
    # Boundary length
    boundary_norm_exp = norm2d_operator(ab_x, ab_y)
    # Distance from the robot to the boundary perpendicular to the boundary segment
    v_dist_exp = divide_operator(abs_operator(cross2d_operator(ab_x, ab_y, ea_x, ea_y)), boundary_norm_exp)
    # Distance between the boundary extreme points and the robot parallel to the boundary segment
    ha_dist_exp = divide_operator(dot2d_operator(ab_x, ab_y, ea_x, ea_y), boundary_norm_exp)
    hb_dist_exp = divide_operator(dot2d_operator(ba_x, ba_y, eb_x, eb_y), boundary_norm_exp)
    # Check for corner cases: robot traj. parallel / perpendicular to boundary
    is_perpendicular_exp = equal_operator(dot2d_operator(ab_x, ab_y, es_x, es_y), 0.0)
    is_parallel_exp = equal_operator(cross2d_operator(ab_x, ab_y, es_x, es_y), 0.0)
    # Interpolation factors
    ha_interp_exp = if_operator(
        and_operator(greater_equal_operator(ha_dist_exp, 0.0), lower_operator(ha_dist_exp, robot_radius)),
        divide_operator(minus_operator(multiply_operator(boundary_norm_exp, robot_radius), dot2d_operator(ab_x, ab_y, ea_x, ea_y)),
                        dot2d_operator(ba_x, ba_y, es_x, es_y)),
        1.0)
    hb_interp_exp = if_operator(
        and_operator(greater_equal_operator(hb_dist_exp, 0.0), lower_operator(hb_dist_exp, robot_radius)),
        divide_operator(minus_operator(multiply_operator(boundary_norm_exp, robot_radius), dot2d_operator(ba_x, ba_y, eb_x, eb_y)),
                        dot2d_operator(ab_x, ab_y, es_x, es_y)),
        1.0)
    h_interp_exp = if_operator(is_perpendicular_exp, 1.0, min_operator(ha_interp_exp, hb_interp_exp))
    v_interp_exp = if_operator(
        or_operator(is_parallel_exp, greater_equal_operator(v_dist_exp, robot_radius)),
        1.0,
        divide_operator(minus_operator(multiply_operator(boundary_norm_exp, robot_radius), abs_operator(cross2d_operator(ab_x, ab_y, ea_x, ea_y))),
                        abs_operator(cross2d_operator(ab_x, ab_y, es_x, es_y))))
    return if_operator(
        greater_equal_operator(max_operator(v_dist_exp, max_operator(ha_dist_exp, hb_dist_exp)), robot_radius),
        0.0, min_operator(h_interp_exp, v_interp_exp))


def __expression_interpolation_next_boundaries(jani_constants: Dict[str, JaniConstant], robot_name, boundary_id) -> JaniExpression:
    n_vertices = jani_constants["boundaries.count"].value()
    assert isinstance(n_vertices, int) and n_vertices > 1, f"The number of boundaries ({n_vertices}) must greater than 1"
    if boundary_id >= n_vertices:
        return JaniExpression(0.0)
    return max_operator(
        __expression_interpolation_single_boundary(jani_constants, robot_name, boundary_id),
        __expression_interpolation_next_boundaries(jani_constants, robot_name, boundary_id + 1))


def __expression_interpolation_next_obstacles(jani_constants, robot_name, obstacle_id) -> JaniExpression:
    # TODO
    return JaniExpression(0.0)


def __expression_interpolation(jani_expression: JaniExpression, jani_constants: Dict[str, JaniConstant]) -> JaniExpression:
    assert isinstance(jani_expression, JaniExpression), "The input must be a JaniExpression"
    assert jani_expression.op == "intersect"
    robot_name = jani_expression.operands["robot"].identifier
    barrier_name = jani_expression.operands["barrier"].identifier
    if barrier_name == "all":
        return max_operator(
            __expression_interpolation_next_boundaries(jani_constants, robot_name, 0),
            __expression_interpolation_next_obstacles(jani_constants, robot_name, 0))
    if barrier_name == "boundaries":
        return __expression_interpolation_next_boundaries(jani_constants, robot_name, 0)
    if barrier_name == "obstacles":
        return __expression_interpolation_next_obstacles(jani_constants, robot_name, 0)
    raise NotImplementedError(f"The barrier type \"{barrier_name}\" is not implemented")


# Functionalities for validity check
def __expression_distance_single_boundary(jani_constants: Dict[str, JaniConstant], robot_name, boundary_id) -> JaniExpression:
    n_vertices = jani_constants["boundaries.count"].value()
    # Variables names
    robot_radius = f"robots.{robot_name}.shape.radius"
    r_x = f"robots.{robot_name}.pose.x"
    r_y = f"robots.{robot_name}.pose.y"
    a_x = f"boundaries.{boundary_id}.x"
    a_y = f"boundaries.{boundary_id}.y"
    b_x = f"boundaries.{(boundary_id + 1) % n_vertices}.x"
    b_y = f"boundaries.{(boundary_id + 1) % n_vertices}.y"
    # Segments expressions
    ab_x = minus_operator(b_x, a_x)
    ab_y = minus_operator(b_y, a_y)
    ba_x = minus_operator(a_x, b_x)
    ba_y = minus_operator(a_y, b_y)
    ra_x = minus_operator(a_x, r_x)
    ra_y = minus_operator(a_y, r_y)
    rb_x = minus_operator(b_x, r_x)
    rb_y = minus_operator(b_y, r_y)
    # All other expressions
    # Boundary length
    boundary_norm_exp = norm2d_operator(ab_x, ab_y)
    # Distance from the robot to the boundary perpendicular to the boundary segment
    v_dist_exp = divide_operator(abs_operator(cross2d_operator(ab_x, ab_y, ra_x, ra_y)), boundary_norm_exp)
    # Distance between the boundary extreme points and the robot parallel to the boundary segment
    ha_dist_exp = divide_operator(dot2d_operator(ab_x, ab_y, ra_x, ra_y), boundary_norm_exp)
    hb_dist_exp = divide_operator(dot2d_operator(ba_x, ba_y, rb_x, rb_y), boundary_norm_exp)
    h_dist_exp = max_operator(max_operator(ha_dist_exp, hb_dist_exp), 0.0)
    return minus_operator(norm2d_operator(h_dist_exp, v_dist_exp), robot_radius)


def __expression_distance_next_boundaries(jani_constants: Dict[str, JaniConstant], robot_name, boundary_id) -> JaniExpression:
    n_vertices = jani_constants["boundaries.count"].value()
    assert isinstance(n_vertices, int) and n_vertices > 1, f"The number of boundaries ({n_vertices}) must greater than 1"
    if boundary_id >= n_vertices:
        return JaniExpression(True)
    return min_operator(
        __expression_distance_single_boundary(jani_constants, robot_name, boundary_id),
        __expression_distance_next_boundaries(jani_constants, robot_name, boundary_id + 1))


def __expression_distance_next_obstacles(jani_constants, robot_name, obstacle_id) -> JaniExpression:
    # TODO
    return JaniExpression(True)


def __expression_distance(jani_expression: JaniExpression, jani_constants: Dict[str, JaniConstant]) -> JaniExpression:
    assert isinstance(jani_expression, JaniExpression), "The input must be a JaniExpression"
    assert jani_expression.op == "distance"
    robot_name = jani_expression.operands["robot"].identifier
    barrier_name = jani_expression.operands["barrier"].identifier
    if barrier_name == "all":
        return min_operator(
            __expression_distance_next_boundaries(jani_constants, robot_name, 0),
            __expression_distance_next_obstacles(jani_constants, robot_name, 0))
    if barrier_name == "boundaries":
        return __expression_distance_next_boundaries(jani_constants, robot_name, 0)
    if barrier_name == "obstacles":
        return __expression_distance_next_obstacles(jani_constants, robot_name, 0)
    raise NotImplementedError("The barrier type is not implemented")


def __expression_distance_to_point(jani_expression: JaniExpression, jani_constants: Dict[str, JaniConstant]) -> JaniExpression:
    assert isinstance(jani_expression, JaniExpression), "The input must be a JaniExpression"
    assert jani_expression.op == "distance_to_point"
    robot_name = jani_expression.operands["robot"].identifier
    target_x_cm = to_cm_operator(expand_expression(jani_expression.operands["x"], jani_constants))
    target_y_cm = to_cm_operator(expand_expression(jani_expression.operands["y"], jani_constants))
    robot_x_cm = f"robots.{robot_name}.pose.x_cm"
    robot_y_cm = f"robots.{robot_name}.pose.y_cm"
    return to_m_operator(norm2d_operator(minus_operator(robot_x_cm, target_x_cm), minus_operator(robot_y_cm, target_y_cm)))


def __substitute_expression_op(expression: JaniExpression) -> JaniExpression:
    assert isinstance(expression, JaniExpression), "The input must be a JaniExpression"
    assert expression.op in BASIC_EXPRESSIONS_MAPPING, f"The operator {expression.op} is not supported"
    expression.op = BASIC_EXPRESSIONS_MAPPING[expression.op]
    return expression


def expand_expression(expression: JaniExpression, jani_constants: Dict[str, JaniConstant]) -> JaniExpression:
    # Given a CONVINCE JaniExpression, expand it to a plain JaniExpression
    assert isinstance(expression, JaniExpression), f"The expression should be a JaniExpression instance, found {type(expression)} instead."
    assert expression.is_valid(), "The expression is not valid: it defines no value, nor variable, nor operation to be done."
    if expression.op is None:
        # It is either a variable/constant identifier or a value
        return expression
    if expression.op == "intersect":
        return __expression_interpolation(expression, jani_constants)
    if expression.op == "distance":
        return __expression_distance(expression, jani_constants)
    if expression.op == "distance_to_point":
        return __expression_distance_to_point(expression, jani_constants)
    # If the expressions is neither of the above, we expand the operands and then we return the expanded expression
    for key, value in expression.operands.items():
        expression.operands[key] = expand_expression(value, jani_constants)
    if expression.op == "norm2d":
        return norm2d_operator(exp=expression)
    if expression.op == "cross2d":
        return cross2d_operator(exp=expression)
    if expression.op == "dot2d":
        return dot2d_operator(exp=expression)
    if expression.op == "to_cm":
        return to_cm_operator(exp=expression)
    if expression.op == "to_m":
        return to_m_operator(exp=expression)
    if expression.op == "to_deg":
        return to_deg_operator(exp=expression)
    if expression.op == "to_rad":
        return to_rad_operator(exp=expression)
    # The remaining operators are the basic ones, and they only need the operand to be substituted
    return __substitute_expression_op(expression)
