# Copyright (c) 2025 - for information on the respective copyright owner
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

from typing import Dict, List, Optional, Type, Union

import esprima
from esprima.syntax import Syntax

from as2fm.as2fm_common.array_type import ArrayInfo, array_value_to_type_info
from as2fm.as2fm_common.common import ValidPlainScxmlTypes

# Definition of a valid ECMAScript expression type
ValidECMAScriptTypes = Union[
    Dict[str, "ValidECMAScriptTypes"], ArrayInfo, Type[ValidPlainScxmlTypes]
]


def get_ast_expression_type(
    ast: esprima.nodes.Node, variables: Dict[str, ValidECMAScriptTypes]
) -> ValidECMAScriptTypes:
    """
    Extracts the type from a given AST expression.

    Valid types are the following:
    - base types (e.g. int, float, string);
    - Arrays (Collection of elements of the same type), represented by an ArrayInfo object
    - objects (a composition of base types, arrays and other objects) represented as a Dict

    :param ast: The AST object containing the expression
    :param variables: Collection of existing variables, and their related types
    """
    return __get_ast_expression_type(ast, variables)


def get_list_from_array_expr(
    ast: esprima.nodes.Node, variables: Dict[str, ValidECMAScriptTypes]
) -> List:
    ret_list: List[Union[ValidPlainScxmlTypes | Dict]] = []
    for elem in ast.elements:
        if elem.type == Syntax.Literal:
            lit_type = __get_ast_literal_type(elem)
            assert lit_type in (
                int,
                float,
            ), f"Found entry of type {lit_type}. Only arrays of int and floats are supported."
            ret_list.append(lit_type(elem.value))
        elif elem.type == Syntax.ArrayExpression:
            ret_list.append(get_list_from_array_expr(elem, variables))
        # elif elem.type == Syntax.ObjectExpression:
        #     extracted_object_types = __get_ast_expression_type(elem, variables)
        #     assert isinstance(extracted_object_types, dict)
        #     ret_list.append(extracted_object_types)
        else:
            raise ValueError(f"Unexpected array element type {elem.type}.")
    return ret_list


def __get_ast_literal_type(ast: esprima.nodes.Node) -> Type[ValidPlainScxmlTypes]:
    """Extract the type of a literal node. Special handling for floats."""
    assert ast.type == Syntax.Literal
    extracted_type = type(ast.value)
    if extracted_type not in (int, float, bool, str):
        raise ValueError(f"Unexpected literal type {extracted_type}.")
    n_dots = ast.raw.count(".")
    if extracted_type is int and n_dots > 0:
        assert n_dots == 1, f"Unexpected literal's raw string {ast.raw}."
        return float
    return extracted_type


def __get_ast_array_expr_type(
    ast: esprima.nodes.Node, variables: Dict[str, ValidECMAScriptTypes]
) -> ArrayInfo:
    assert ast.type == Syntax.ArrayExpression
    converted_array = get_list_from_array_expr(ast, variables)
    return array_value_to_type_info(converted_array)


def __get_member_access_name(ast: esprima.nodes.Node) -> str:
    """Compute the name resulting from a non-computed MemberExpression."""
    assert ast.type == Syntax.MemberExpression and not ast.computed
    member_obj_name: str = ""
    if ast.object.type == Syntax.Identifier:
        member_obj_name = ast.object.name
    else:
        member_obj_name = __get_member_access_name(ast.object)
    member_prop_name: str = ""
    if ast.property.type == Syntax.Identifier:
        member_prop_name = ast.property.name
    else:
        member_prop_name = __get_member_access_name(ast.property)
    return f"{member_obj_name}.{member_prop_name}"


def __get_member_access_array(
    ast: esprima.nodes.Node, variables: Dict[str, ValidECMAScriptTypes]
) -> ValidECMAScriptTypes:
    """
    Compute the type resulting from an array access operator.

    Note: In this functions, we assume that all array access operators are at the end.
    E.g. obj.some_array[0][1][2] and not obj_array[0].something[1].x[2]
    """
    assert ast.type == Syntax.MemberExpression and ast.computed
    depth = 1
    curr_ast = ast.object
    while curr_ast.type != Syntax.Identifier:
        assert curr_ast.type == Syntax.MemberExpression and curr_ast.computed
        curr_ast = curr_ast.object
        depth += 1
    var_type = variables[curr_ast.name]
    assert isinstance(var_type, ArrayInfo), f"{var_type=} != ArrayInfo."
    if depth == var_type.array_dimensions:
        return var_type.array_type
    elif depth < var_type.array_dimensions:
        return ArrayInfo(
            var_type.array_type, var_type.array_dimensions - depth, var_type.array_max_sizes[depth:]
        )
    raise RuntimeError(
        f"Invalid array access: trying to access the {depth}-th dim. "
        f"of a {var_type.array_dimensions}-dim array."
    )


def __get_call_expr_type(
    ast: esprima.nodes.Node, variables: Dict[str, ValidECMAScriptTypes]
) -> Type[ValidPlainScxmlTypes]:
    assert ast.type == Syntax.CallExpression
    callee_str: str = ""
    if ast.callee.type == Syntax.Identifier:
        callee_str = ast.callee.name
    else:
        callee_str = __get_member_access_name(ast.callee)
    if callee_str in ("Math.cos", "Math.sin", "Math.log", "Math.pow", "Math.random"):
        return float
    elif callee_str in ("Math.floor", "Math.ceil"):
        return int
    elif callee_str in ("Math.abs", "Math.min", "Math.max"):
        found_type: Optional[Union[Type[int], Type[float]]] = None
        for callee_arg in ast.arguments:
            arg_type = __get_ast_expression_type(callee_arg, variables)
            assert arg_type in (int, float)
            if found_type is not float:
                found_type = arg_type
        assert found_type is not None
        return found_type
    raise RuntimeError(f"Unknown function in expression: {callee_str}.")


def __get_unary_expr_type(
    ast: esprima.nodes.Node, variables: Dict[str, ValidECMAScriptTypes]
) -> Type[ValidPlainScxmlTypes]:
    assert ast.type == Syntax.UnaryExpression
    assert ast.prefix is True
    op_arg_type = __get_ast_expression_type(ast.argument, variables)
    op = ast.operator
    if op == "-":
        assert op_arg_type in (int, float)
        return op_arg_type
    elif op == "!":
        assert op_arg_type is bool
        return op_arg_type
    raise RuntimeError(f"Unexpected unary operator. '{op}' not in ('-', '!').")


def __get_binary_expr_type(
    ast: esprima.nodes.Node, variables: Dict[str, ValidECMAScriptTypes]
) -> Type[ValidPlainScxmlTypes]:
    assert ast.type == Syntax.BinaryExpression
    left_type = __get_ast_expression_type(ast.left, variables)
    right_type = __get_ast_expression_type(ast.right, variables)
    op = ast.operator

    # Arithmetic operators
    if op in ("+", "-", "*", "/", "%", "**"):
        # If either side is float, result is float
        if float in (left_type, right_type):
            return float
        # Both int
        return int

    # Comparison operator
    if op in (">", ">=", "<", "<=", "==", "!="):
        return bool

    raise ValueError(f"Unknown binary operator: {op}")


def __get_ast_expression_type(
    ast: esprima.nodes.Node, variables: Dict[str, ValidECMAScriptTypes]
) -> ValidECMAScriptTypes:
    if ast.type == Syntax.Literal:
        return __get_ast_literal_type(ast)
    elif ast.type == Syntax.Identifier:
        return variables[ast.name]
    elif ast.type == Syntax.ArrayExpression:
        return __get_ast_array_expr_type(ast, variables)
    elif ast.type == Syntax.MemberExpression:
        if ast.computed:
            # Array Access Operator
            return __get_member_access_array(ast, variables)
        else:
            # Member access operator, treat it like an identifier
            return variables[__get_member_access_name(ast)]
    elif ast.type == Syntax.CallExpression:
        return __get_call_expr_type(ast, variables)
    elif ast.type == Syntax.LogicalExpression:
        assert __get_ast_expression_type(ast.left, variables) is bool
        assert __get_ast_expression_type(ast.right, variables) is bool
        return bool
    elif ast.type == Syntax.BinaryExpression:
        return __get_binary_expr_type(ast, variables)
    elif ast.type == Syntax.UnaryExpression:
        return __get_unary_expr_type(ast, variables)
    elif ast.type == Syntax.ObjectExpression:
        obj_dict = {}
        for property in ast.properties:
            assert property.key.type == Syntax.Literal, "Property key must be literal."
            obj_dict[property.key.value] = __get_ast_expression_type(property.value, variables)
        return obj_dict
    else:
        raise ValueError(f"Unknown ast type {ast.type}")


def get_dict_from_object_expression(
    ast: esprima.nodes.Node,
) -> Dict[str, Union[Dict, List, esprima.nodes.Node]]:
    """Parse and AST expression and extracts the resulting value."""
    assert ast.type == Syntax.ObjectExpression
    expanded_node = __expand_ast_expression_object(ast)
    assert isinstance(expanded_node, dict)
    return expanded_node


def __expand_ast_expression_object(
    ast: esprima.nodes.Node,
) -> Union[Dict[str, Union[Dict, List, esprima.nodes.Node]], esprima.nodes.Node, List]:
    """Implementation of 'get_dict_from_object_expression'."""
    # Base AST expressions: keep as they are
    if ast.type == Syntax.Literal:
        return ast
    elif ast.type == Syntax.CallExpression:
        return ast
    elif ast.type == Syntax.LogicalExpression:
        return ast
    elif ast.type == Syntax.BinaryExpression:
        return ast
    elif ast.type == Syntax.UnaryExpression:
        return ast
    # Arrays might contain further object definitions: recurse!
    elif ast.type == Syntax.ArrayExpression:
        return [__expand_ast_expression_object(array_node) for array_node in ast.elements]
    # Each entry in the Object definition can, in turn, be an object (or an array): recurse!
    elif ast.type == Syntax.ObjectExpression:
        return {
            prop.key.value: __expand_ast_expression_object(prop.value) for prop in ast.properties
        }
    else:
        raise ValueError(f"Cannot use AST node of type {ast.type} in data object definition.")
