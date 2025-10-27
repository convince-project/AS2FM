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
from typing import Any, Dict, List, Optional, Tuple, Type

import esprima
from esprima.nodes import ArrayExpression, ComputedMemberExpression, Identifier, Literal
from esprima.syntax import Syntax
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.ecmascript_interpretation import (
    MemberAccessCheckException,
    ast_expression_to_string,
    has_array_access,
    parse_expression_to_ast,
    split_by_access,
)
from as2fm.as2fm_common.logging import check_assertion, get_error_msg, log_error
from as2fm.scxml_converter.data_types.type_utils import (
    ARRAY_LENGTH_SUFFIX,
    MEMBER_ACCESS_SUBSTITUTION,
)
from as2fm.scxml_converter.scxml_entries.scxml_base import ScxmlBase
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer

PLAIN_EVENT_KEY: str = "_event"
PLAIN_SCXML_EVENT_PREFIX: str = f"{PLAIN_EVENT_KEY}."
PLAIN_EVENT_DATA_KEY: str = "data"
PLAIN_SCXML_EVENT_DATA_PREFIX: str = PLAIN_SCXML_EVENT_PREFIX + PLAIN_EVENT_DATA_KEY + "."

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


def generate_tag_to_class_map(cls: Type[ScxmlBase]) -> Dict[str, Type[ScxmlBase]]:
    """
    Generate a map from (xml) tags to their associated classes.

    The map is generated for the provided class and all its subclasses.
    """
    ret_dict: Dict[str, Type[ScxmlBase]] = {}
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
    """Check if string expression contains prefixes like `_event.`."""
    for prefix in prefixes:
        prefix_reg = prefix.replace(".", r"\.")
        if re.search(rf"(^|[^a-zA-Z0-9_.]){prefix_reg}", msg_expr) is not None:
            return True
    return False


def get_plain_variable_name(in_name: str, xml_origin: Optional[XmlElement]) -> str:
    """Given a variable or param name with member access, generate the plain version with '__'."""
    check_assertion(
        not has_array_access(in_name, xml_origin),
        xml_origin,
        f"Provided variable {in_name} contains array accesses, too.",
    )
    expanded_name = split_by_access(in_name, xml_origin)
    return MEMBER_ACCESS_SUBSTITUTION.join(expanded_name)


def get_plain_expression(
    in_expr: str,
    cb_type: CallbackType,
    struct_declarations: Optional[ScxmlStructDeclarationsContainer],
) -> str:
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
        f"Error: SCXML-ROS expression conversion with Cb type {cb_type.name}: "
        f"unexpected ROS interface prefixes in expr.: {in_expr}"
    )
    # arrays of custom structs
    new_expr = convert_expression_with_object_arrays(new_expr, None, struct_declarations)
    return new_expr


def _reassemble_expression(
    array: esprima.nodes.Node, idxs: List[esprima.nodes.Node]
) -> esprima.nodes.Node:
    """
    Turn AST that was split between member and array access by `_split_array_indexes_out`
    back into one expression.
    """
    if len(idxs) == 0:
        return array
    return _reassemble_expression(ComputedMemberExpression(array, idxs[0]), idxs[1:])


def _is_member_expr_event_data(node: Optional[esprima.nodes.Node]):
    """Check if the AST node contains _event.data"""
    if node is None:
        return False
    if node.type == Syntax.MemberExpression and not node.computed:
        if node.object.type == Syntax.Identifier and node.property.type == Syntax.Identifier:
            if node.object.name == PLAIN_EVENT_KEY and node.property.name == PLAIN_EVENT_DATA_KEY:
                return True
    return False


def _convert_non_computed_member_exprs_to_identifiers(
    node: esprima.nodes.Node, parent_node: Optional[esprima.nodes.Node]
) -> esprima.nodes.Node:
    """Convert member access operators (like '.') into identifiers 'a__b' or '_event.data.b')."""
    if node.type == Syntax.Identifier:
        if node.name == ARRAY_LENGTH_SUFFIX and (
            parent_node is None or parent_node.type != Syntax.MemberExpression
        ):
            raise MemberAccessCheckException(
                f"{ARRAY_LENGTH_SUFFIX} is a reserved keyword. Cannot be used here."
            )
        return node
    elif node.type == Syntax.Literal:
        return node
    elif node.type == Syntax.MemberExpression:
        # If not array index, convert to identifier
        node.object = _convert_non_computed_member_exprs_to_identifiers(node.object, node)
        node.property = _convert_non_computed_member_exprs_to_identifiers(node.property, node)
        if node.computed:
            # This is an array index access operator: do not convert it to an identifier.
            return node
        if node.property.type == Syntax.Identifier and node.property.name == ARRAY_LENGTH_SUFFIX:
            # We are accessing the length field: this is a special keyword, keep the dot.
            if (
                parent_node is not None
                and parent_node.type == Syntax.MemberExpression
                and not parent_node.computed
            ):
                raise MemberAccessCheckException(
                    f"{ARRAY_LENGTH_SUFFIX} is a reserved keyword. Cannot be used here."
                )
            return node
        # If here, this is a member entry access
        assert node.object.type == Syntax.Identifier, f"Error: unexpected node content in {node}"
        assert node.property.type == Syntax.Identifier, f"Error: unexpected node content in {node}"
        member_separator = MEMBER_ACCESS_SUBSTITUTION
        # Special casing, for preserving the "_event.data.<param_1>__<param_2>" notation
        if _is_member_expr_event_data(node) or node.object.name == (
            PLAIN_SCXML_EVENT_PREFIX + PLAIN_EVENT_DATA_KEY
        ):
            member_separator = "."
        return Identifier(f"{node.object.name}{member_separator}{node.property.name}")
    elif node.type in (Syntax.BinaryExpression, Syntax.LogicalExpression):
        node.left = _convert_non_computed_member_exprs_to_identifiers(node.left, node)
        node.right = _convert_non_computed_member_exprs_to_identifiers(node.right, node)
        return node
    elif node.type == Syntax.CallExpression:
        node.arguments = [
            _convert_non_computed_member_exprs_to_identifiers(node_arg, node)
            for node_arg in node.arguments
        ]
        return node
    elif node.type == Syntax.UnaryExpression:
        node.argument = _convert_non_computed_member_exprs_to_identifiers(node.argument, node)
        return node
    else:
        raise NotImplementedError(get_error_msg(None, f"Unhandled expression type: {node.type}"))


def _assemble_object_for_length_access(
    ast_array: esprima.nodes.Node,
    array_idxs: List[esprima.nodes.Node],
    struct_declarations: Optional[ScxmlStructDeclarationsContainer],
) -> esprima.nodes.Node:
    """
    Generate the ast expression for accessing length information of custom structs.

    This is about accessing the length of an array of objects in HL-SCXML. In LL-SCXML, we
    don't consider objects, so they are translated to flat arrays of their base-type
    properties. Then, the length has to return the length of a (the first) of the structs properties
    lengths.

    e.g. for `points: {x: [2, 4, 5], y: [1, 0, 8]}`
    then `points.length` should be translated to `points.x.length` (later to `points__x.length`)
    """
    if struct_declarations is None:
        # In this case, we expect the ast_array to be a simple identifier with no indexes.
        if ast_array.type != Syntax.Identifier or len(array_idxs) > 0:
            raise AttributeError("Trying to access a member length, but no struct def. provided.")
        return _reassemble_expression(ast_array, array_idxs)
    # Generate the member access expression w.o. index access
    member_var = ast_expression_to_string(ast_array)
    data_type, _ = struct_declarations.get_data_type(member_var, None)
    if isinstance(data_type, str):
        # not an object (a base type)
        return _reassemble_expression(ast_array, array_idxs)
    all_expanded_members = [k for k in data_type.get_expanded_members().keys()]
    expanded_member_node = parse_expression_to_ast(f"{member_var}.{all_expanded_members[0]}", None)
    return _reassemble_expression(expanded_member_node, array_idxs)


def _split_array_indexes_out(
    ast: esprima.nodes.Node, struct_declarations: Optional[ScxmlStructDeclarationsContainer]
) -> Tuple[esprima.nodes.Node, List[esprima.nodes.Node]]:
    """
    Split expression between member access and array access, needed to represent arrays of custom
    objects as arrays of their properties, instead.

    `a[0]` => 'a', ['0']
    `a[0].x` => 'a.x', ['0']
    `a[0].x[2]` => 'a.x', ['0', '2']
    `a` => 'a', []
    """
    if ast.type in (Syntax.Identifier, Syntax.Literal):
        return ast, []
    elif ast.type == Syntax.MemberExpression:
        obj, obj_idxs = _split_array_indexes_out(ast.object, struct_declarations)
        if ast.computed:  # array index
            return obj, obj_idxs + [
                _reassemble_expression(*_split_array_indexes_out(ast.property, struct_declarations))
            ]
        # actual member access
        if ast.property.name == ARRAY_LENGTH_SUFFIX:
            # If the object refers to a struct (instead of an array), add missing members
            ast.object = _assemble_object_for_length_access(obj, obj_idxs, struct_declarations)
            return ast, []  # no indexes after length property
        ast.object = _reassemble_expression(*_split_array_indexes_out(obj, struct_declarations))
        return ast, obj_idxs
    elif ast.type in (Syntax.BinaryExpression, Syntax.LogicalExpression):
        ast.left = _reassemble_expression(*_split_array_indexes_out(ast.left, struct_declarations))
        ast.right = _reassemble_expression(
            *_split_array_indexes_out(ast.right, struct_declarations)
        )
        return ast, []
    elif ast.type == Syntax.CallExpression:
        ast.arguments = [
            _reassemble_expression(*_split_array_indexes_out(a, struct_declarations))
            for a in ast.arguments
        ]
        return ast, []
    elif ast.type == Syntax.UnaryExpression:
        ast.argument = _reassemble_expression(
            *_split_array_indexes_out(ast.argument, struct_declarations)
        )
        return ast, []
    else:
        raise NotImplementedError(get_error_msg(None, f"Unhandled expression type: {ast.type}"))


def _convert_string_literals_to_int_arrays(node: esprima.nodes.Node) -> esprima.nodes.Node:
    """
    Convert all string literals in the expression to an array of ints.
    """
    if node.type == Syntax.Identifier:
        return node
    elif node.type == Syntax.Literal:
        if isinstance(node.value, str):
            # Found a string, convert it to an array of ints
            return ArrayExpression([Literal(x, str(x)) for x in node.value.encode()])
        return node
    elif node.type == Syntax.ArrayExpression:
        return ArrayExpression(
            [_convert_string_literals_to_int_arrays(entry) for entry in node.elements]
        )
    elif node.type == Syntax.MemberExpression:
        return node
    elif node.type in (Syntax.BinaryExpression, Syntax.LogicalExpression):
        node.left = _convert_string_literals_to_int_arrays(node.left)
        node.right = _convert_string_literals_to_int_arrays(node.right)
        return node
    elif node.type == Syntax.CallExpression:
        node.arguments = [
            _convert_string_literals_to_int_arrays(node_arg) for node_arg in node.arguments
        ]
        return node
    elif node.type == Syntax.UnaryExpression:
        node.argument = _convert_string_literals_to_int_arrays(node.argument)
        return node
    else:
        raise NotImplementedError(get_error_msg(None, f"Unhandled expression type: {node.type}"))


def convert_expression_with_object_arrays(
    expr: str,
    elem: Optional[XmlElement] = None,
    struct_declarations: Optional[ScxmlStructDeclarationsContainer] = None,
) -> str:
    """
    e.g. `my_polygons.polygons[0].points[1].y` => `my_polygons__polygons__points__y[0][1]`.
    """
    try:
        ast = parse_expression_to_ast(expr, elem)
        obj, idxs = _split_array_indexes_out(ast, struct_declarations)
        exp = _reassemble_expression(obj, idxs)
        exp = _convert_non_computed_member_exprs_to_identifiers(exp, None)
    except MemberAccessCheckException as e:
        log_error(elem, "Failed to expand the provided expression.")
        raise e
    return ast_expression_to_string(exp)


def convert_expression_with_string_literals(
    expr: str,
    elem: Optional[XmlElement] = None,
) -> str:
    """
    Convert an expression with strings to use array of ints instead.

    e.g. `'as2fm'` => `[97, 115, 50, 102, 109]`
    """
    try:
        ast = parse_expression_to_ast(expr, elem)
        exp = _convert_string_literals_to_int_arrays(ast)
    except MemberAccessCheckException as e:
        log_error(elem, "Failed to expand the provided expression.")
        raise e
    return ast_expression_to_string(exp)


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


def is_non_empty_string(
    scxml_type: Type[ScxmlBase], arg_name: str, arg_value: Optional[Any]
) -> bool:
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


def to_integer(scxml_type: Type[ScxmlBase], arg_name: str, arg_value: str) -> Optional[int]:
    """
    Try to convert a string to an integer. Return None if not possible.
    """
    arg_value = arg_value.strip()
    assert is_non_empty_string(scxml_type, arg_name, arg_value)
    try:
        return int(arg_value)
    except ValueError:
        return None
