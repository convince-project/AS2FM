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
# limitations under the License.

"""Collection of various utilities for SCXML entries."""

import re
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Type

import esprima

from as2fm.as2fm_common.logging import get_error_msg
from as2fm.scxml_converter.scxml_entries.scxml_base import ScxmlBase
from as2fm.scxml_converter.xml_data_types.xml_struct_definition import XmlStructDefinition

ARRAY_LENGTH_SUFFIX = "length"

# List of names that shall not be used for variable names
RESERVED_NAMES: List[str] = []

PLAIN_SCXML_EVENT_PREFIX: str = "_event."
PLAIN_SCXML_EVENT_DATA_PREFIX: str = PLAIN_SCXML_EVENT_PREFIX + "data."

# Constants related to the conversion of expression from ROS to plain SCXML
ROS_FIELD_PREFIX: str = "ros_fields__"
PLAIN_FIELD_EVENT_PREFIX: str = PLAIN_SCXML_EVENT_DATA_PREFIX + ROS_FIELD_PREFIX

ROS_EVENT_PREFIXES = [
    "_msg.",  # Topic-related
    "_req.",
    "_res.",  # Service-related
    "_goal.",
    "_feedback.",
    "_wrapped_result.",
    "_action.",  # Action-related
]


# ------------ Expression-conversion functionalities ------------
class CallbackType(Enum):
    """Enumeration of the different types of callbacks containing a body."""

    STATE = auto()  # No callback (e.g. state entry/exit)
    TRANSITION = auto()  # Transition callback
    ROS_TIMER = auto()  # Timer callback
    ROS_TOPIC = auto()  # Topic callback
    ROS_SERVICE_REQUEST = auto()  # Service callback
    ROS_SERVICE_RESULT = auto()  # Service callback
    ROS_ACTION_GOAL = auto()  # Action callback
    ROS_ACTION_RESULT = auto()  # Action callback
    ROS_ACTION_FEEDBACK = auto()  # Action callback
    BT_RESPONSE = auto()  # BT response callback

    @staticmethod
    def get_expected_prefixes(cb_type: "CallbackType") -> List[str]:
        if cb_type in (CallbackType.STATE, CallbackType.ROS_TIMER):
            return []
        elif cb_type == CallbackType.TRANSITION:
            return [PLAIN_SCXML_EVENT_DATA_PREFIX]
        elif cb_type == CallbackType.ROS_TOPIC:
            return ["_msg."]
        elif cb_type == CallbackType.ROS_SERVICE_REQUEST:
            return ["_req."]
        elif cb_type == CallbackType.ROS_SERVICE_RESULT:
            return ["_res."]
        elif cb_type == CallbackType.ROS_ACTION_GOAL:
            return ["_action.goal_id", "_goal."]
        elif cb_type == CallbackType.ROS_ACTION_RESULT:
            return ["_action.goal_id", "_wrapped_result.code", "_wrapped_result.result."]
        elif cb_type == CallbackType.ROS_ACTION_FEEDBACK:
            return ["_action.goal_id", "_feedback."]
        elif cb_type == CallbackType.BT_RESPONSE:
            return ["_bt.status"]
        raise ValueError(f"Unexpected CallbackType {cb_type}")

    @staticmethod
    def get_plain_callback(cb_type: "CallbackType") -> "CallbackType":
        """Convert ROS-specific transitions to plain ones."""
        if cb_type == CallbackType.STATE:
            return CallbackType.STATE
        else:
            return CallbackType.TRANSITION


def generate_tag_to_class_map(cls: Type["ScxmlBase"]) -> Dict[str, Type["ScxmlBase"]]:
    """
    Generate a map from (xml) tags to their associated classes.

    The map is generated for the provided class and all its subclasses.
    """
    ret_dict: Dict[str, Type["ScxmlBase"]] = {}
    try:
        tag_name = cls.get_tag_name()
        ret_dict.update({tag_name: cls})
    except NotImplementedError:
        pass
    for sub_cls in cls.__subclasses__():
        ret_dict.update(generate_tag_to_class_map(sub_cls))
    return ret_dict


def _replace_ros_interface_expression(msg_expr: str, expected_prefixes: List[str]) -> str:
    """
    Given an expression with the ROS entries from a list, it generates a plain SCXML expression.

    :param msg_expr: The expression to convert.
    :param expected_prefixes: The list of (ROS) prefixes that are expected in the expression.
    """

    if PLAIN_SCXML_EVENT_DATA_PREFIX in expected_prefixes:
        expected_prefixes.remove(PLAIN_SCXML_EVENT_DATA_PREFIX)
    msg_expr.strip()
    for prefix in expected_prefixes:
        assert prefix.startswith(
            "_"
        ), f"Error: SCXML ROS conversion: prefix {prefix} does not start with underscore."
        if prefix.endswith("."):
            # Generic field substitution, adding the ROS_FIELD_PREFIX
            prefix_reg = prefix.replace(".", r"\.")
            msg_expr = re.sub(
                rf"(^|[^a-zA-Z0-9_.]){prefix_reg}([a-zA-Z0-9_.])",
                rf"\g<1>{PLAIN_FIELD_EVENT_PREFIX}\g<2>",
                msg_expr,
            )
        else:
            # Special fields substitution, no need to add the ROS_FIELD_PREFIX
            split_prefix = prefix.split(".", maxsplit=1)
            assert (
                len(split_prefix) == 2
            ), f"Error: SCXML ROS conversion: prefix {prefix} has no dots."
            substitution = f"{PLAIN_SCXML_EVENT_DATA_PREFIX}{split_prefix[1]}"
            prefix_reg = prefix.replace(".", r"\.")
            msg_expr = re.sub(
                rf"(^|[^a-zA-Z0-9_.]){prefix_reg}($|[^a-zA-Z0-9_.])",
                rf"\g<1>{substitution}\g<2>",
                msg_expr,
            )
    return msg_expr


def _contains_prefixes(msg_expr: str, prefixes: List[str]) -> bool:
    for prefix in prefixes:
        prefix_reg = prefix.replace(".", r"\.")
        if re.search(rf"(^|[^a-zA-Z0-9_.]){prefix_reg}", msg_expr) is not None:
            return True
    return False


def get_plain_expression(in_expr: str, cb_type: CallbackType) -> str:
    """
    Convert ROS-specific PREFIXES, custom struct array indexing to plain SCXML.

    e.g. `_msg.a` => `_event.data.a` and
         `objects[2].x` => `objects.x[2]`

    :param in_expr: The expression to convert.
    :param cb_type: The type of callback the expression is used in.
    """
    expected_prefixes = CallbackType.get_expected_prefixes(cb_type)
    # pre-check over the expression
    if PLAIN_SCXML_EVENT_DATA_PREFIX not in expected_prefixes:
        assert not _contains_prefixes(in_expr, [PLAIN_SCXML_EVENT_DATA_PREFIX]), (
            "Error: SCXML-ROS expression conversion: "
            f"unexpected {PLAIN_SCXML_EVENT_DATA_PREFIX} prefix in expr. {in_expr}"
        )
    forbidden_prefixes = ROS_EVENT_PREFIXES.copy()
    if len(expected_prefixes) == 0:
        forbidden_prefixes.append(PLAIN_SCXML_EVENT_DATA_PREFIX)
    new_expr = _replace_ros_interface_expression(in_expr, expected_prefixes)
    assert not _contains_prefixes(new_expr, forbidden_prefixes), (
        "Error: SCXML-ROS expression conversion: "
        f"unexpected ROS interface prefixes in expr.: {in_expr}"
    )
    # arrays of custom structs
    new_expr = convert_expression_with_object_arrays(new_expr)
    return new_expr


def _separated_member_expression_to_str(obj, idxs) -> str:
    return obj + "".join([f"[{x}]" for x in idxs])


def _convert_ast_to_plain_str(ast: esprima.nodes.Node) -> Tuple[str, List[str]]:
    """
    `a[0]` => 'a', ['0']
    `a[0].x` => 'a.x', ['0']
    `a[0].x[2]` => 'a.x', ['0', '2']
    `a` => 'a', []
    """
    if ast.type == "Identifier":
        return ast.name, []
    elif ast.type == "Literal":
        return ast.raw, []
    elif ast.type == "MemberExpression":
        obj, idxs = _convert_ast_to_plain_str(ast.object)
        if ast.computed:  # array index
            idx_expr = _convert_ast_to_plain_str(ast.property)
            idx_str = _separated_member_expression_to_str(*idx_expr)
            return obj, idxs + [idx_str]
        else:  # actual member access
            if ast.property.name == ARRAY_LENGTH_SUFFIX:
                obj = _separated_member_expression_to_str(obj, idxs)
                return f"{obj}.{ast.property.name}", []
            return f"{obj}.{ast.property.name}", idxs
    elif ast.type in ("BinaryExpression", "LogicalExpression"):
        left_expr = _convert_ast_to_plain_str(ast.left)
        right_expr = _convert_ast_to_plain_str(ast.right)
        left_str = _separated_member_expression_to_str(*left_expr)
        right_str = _separated_member_expression_to_str(*right_expr)
        return f"({left_str} {ast.operator} {right_str})", []
    elif ast.type == "CallExpression":
        callee_expr = _convert_ast_to_plain_str(ast.callee)
        argument_exprs = [_convert_ast_to_plain_str(a) for a in ast.arguments]
        callee_str = _separated_member_expression_to_str(*callee_expr)
        argument_strs = [_separated_member_expression_to_str(*a) for a in argument_exprs]
        arguments_str = ", ".join(argument_strs)
        return f"{callee_str}({arguments_str})", []
    elif ast.type == "UnaryExpression":
        operator = ast.operator
        expr_vals = _convert_ast_to_plain_str(ast.argument)
        expr_str = _separated_member_expression_to_str(*expr_vals)
        if ast.argument.type not in ("Identifier", "Literal"):
            expr_str = f"({expr_str})"
        return f"{operator}{expr_str}", []
    else:
        raise NotImplementedError(get_error_msg(None, f"Unhandled expression type: {ast.type}"))


def convert_expression_with_object_assignment(
    expr: str, custom_data_type: XmlStructDefinition, elem=None
) -> List[str]:
    """
    e.g. `x.ps[0]` =>
         `['x.ps[0].x', 'x.ps[0].y']`.

    """
    raise NotImplementedError("todo ...")


def convert_expression_with_object_arrays(expr: str, elem=None) -> str:
    """
    e.g. `my_polygons.polygons[0].points[1].y` => `my_polygons.polygons.points.y[0][1]`.
    """
    try:
        ast = esprima.parseScript(expr)
    except esprima.error_handler.Error as e:
        raise RuntimeError(get_error_msg(elem, f"Failed parsing ecmascript: {expr}. Error: {e}."))
    assert len(ast.body) == 1, get_error_msg(
        elem, "The ecmascript must contain exactly one expression."
    )
    ast = ast.body[0]
    assert ast.type == "ExpressionStatement", get_error_msg(
        elem, "The ecmascript must contain exactly one expression."
    )
    ast = ast.expression
    print(expr)
    print(ast)
    print(_convert_ast_to_plain_str(ast))

    obj, idxs = _convert_ast_to_plain_str(ast)

    return _separated_member_expression_to_str(obj, idxs)


# ------------ String-related utilities ------------
def all_non_empty_strings(*in_args) -> bool:
    """
    Check if all the arguments are non-empty strings.

    :param kwargs: The arguments to be checked.
    :return: True if all the arguments are non-empty strings, False otherwise.
    """
    for arg_value in in_args:
        if not isinstance(arg_value, str) or len(arg_value) == 0:
            return False
    return True


def is_non_empty_string(scxml_type: Type["ScxmlBase"], arg_name: str, arg_value: str) -> bool:
    """
    Check if a string is non-empty.

    :param scxml_type: The scxml entry where this function is called, to write error msgs.
    :param arg_name: The name of the argument, to write error msgs.
    :param arg_value: The value of the argument to be checked.
    :return: True if the string is non-empty, False otherwise.
    """
    valid_str = isinstance(arg_value, str) and len(arg_value.strip()) > 0
    if not valid_str:
        print(
            f"Error: SCXML entry from {scxml_type.__name__}: "
            f"Expected non-empty argument {arg_name}, got >{arg_value}<."
        )
    return valid_str


def to_integer(scxml_type: Type["ScxmlBase"], arg_name: str, arg_value: str) -> Optional[int]:
    """
    Try to convert a string to an integer. Return None if not possible.
    """
    arg_value = arg_value.strip()
    assert is_non_empty_string(scxml_type, arg_name, arg_value)
    try:
        return int(arg_value)
    except ValueError:
        return None
