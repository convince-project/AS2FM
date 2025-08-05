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

"""
Utilities for handling AST expressions.
"""

from typing import List, Type, Union

from esprima.nodes import ArrayExpression, Syntax


def get_type_ast_array_expression(array_ast: ArrayExpression) -> Type[Union[int, float]]:
    """Generate the ArrayInfo associated to the input AST instance."""
    assert array_ast.type == Syntax.ArrayExpression, "This function expects an ArrayExpression."
    expected_type: Type[Union[int, float]] = int
    sub_array_found = False
    sub_literal_found = False
    for sub_expr in array_ast.elements:
        if sub_expr.type == Syntax.ArrayExpression:
            sub_array_found = True
            sub_type = get_type_ast_array_expression(sub_expr)
        elif sub_expr.type == Syntax.Literal:
            sub_literal_found = True
            sub_type = type(sub_expr.value)
        assert not (
            sub_array_found and sub_literal_found
        ), "Found arrays and lit. values at the same array level."
        if sub_type == float:
            expected_type = float
    return expected_type


def ast_array_expression_to_list(
    array_ast: ArrayExpression, array_type: Type[Union[int, float]]
) -> List[Union[int, float, List]]:
    """
    Convert an AST expression to a python list.

    :param array_ast: The array expression node
    :param array_type: The type of the array entries
    """
    assert array_ast.type == Syntax.ArrayExpression, "This function expects an ArrayExpression."
    result: List[Union[int, float, List]] = []
    for elem in array_ast.elements:
        if elem.type == Syntax.ArrayExpression:
            result.append(ast_array_expression_to_list(elem, array_type))
        elif elem.type == Syntax.Literal:
            value = elem.value
            if array_type == float:
                value = float(value)
            elif array_type == int:
                value = int(value)
            result.append(value)
        else:
            raise ValueError(f"Unsupported AST node type: {elem.type}")
    return result
