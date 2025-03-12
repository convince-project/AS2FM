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
Module defining SCXML tags to match against.
"""

from typing import Dict, List, Optional, get_args

from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.common import (
    ValidTypes,
    get_default_expression_for_type,
    is_array_type,
    string_to_value,
)
from as2fm.jani_generator.jani_entries import (
    JaniAssignment,
    JaniExpression,
    JaniExpressionType,
    JaniVariable,
)
from as2fm.jani_generator.jani_entries.jani_expression_generator import (
    array_create_operator,
    max_operator,
    plus_operator,
)
from as2fm.jani_generator.jani_entries.jani_utils import (
    get_array_variable_info,
    is_expression_array,
    is_variable_array,
)
from as2fm.jani_generator.scxml_helpers.scxml_expression import (
    ArrayInfo,
    parse_ecmascript_to_jani_expression,
)


def generate_jani_assignments(
    target_expr: JaniExpression,
    assign_expr: str,
    context_vars: Dict[str, JaniVariable],
    event_substitution: Optional[str],
    assign_index: int,
    elem_xml: XmlElement,
) -> List[JaniAssignment]:
    """Interpret SCXML assign element.

    :param element: The SCXML element to interpret.
    :param jani_automaton: The Jani automaton related to the current scxml. Used for variable types.
    :param event_substitution: The event to substitute in the expression.
    :return: The action or expression to be executed.
    """
    assignments: List[JaniAssignment] = []
    target_expr_type = target_expr.get_expression_type()
    # An assignment target must be either a variable or a single array entry
    if target_expr_type is JaniExpressionType.OPERATOR:
        # If here, the target expression must be an array access (aa) operator
        assign_op_name, assign_operands = target_expr.as_operator()
        assert assign_op_name == "aa", f"Unexpected assignment target: {assign_op_name} != 'aa'."
        assignment_value = parse_ecmascript_to_jani_expression(
            assign_expr, elem_xml, None
        ).replace_event(event_substitution)
        assignments.append(
            JaniAssignment({"ref": target_expr, "value": assignment_value, "index": assign_index})
        )
        target_var_length = f"{assign_operands['exp'].as_identifier()}.length"
        new_array_legth_expr = max_operator(
            plus_operator(assign_operands["index"], 1), target_var_length
        )
        assignments.append(
            JaniAssignment(
                {
                    "ref": target_var_length,
                    "value": new_array_legth_expr,
                    "index": assign_index,
                }
            )
        )
    else:
        # In this case, we expect the assign target to be a variable
        assignment_target_id = target_expr.as_identifier()
        assert (
            assignment_target_id is not None
        ), "Assignment targets must be either variables or array elements"
        assignment_target_variable = context_vars.get(assignment_target_id)
        assert (
            assignment_target_variable is not None
        ), f"Can't find variable {assignment_target_id} in the provided context {context_vars}."
        array_info = None
        if is_variable_array(assignment_target_variable):
            array_info = ArrayInfo(*get_array_variable_info(assignment_target_variable))
        assignment_value = parse_ecmascript_to_jani_expression(
            assign_expr, elem_xml, array_info
        ).replace_event(event_substitution)
        assignments.append(
            JaniAssignment({"ref": target_expr, "value": assignment_value, "index": assign_index})
        )
        # In case this is an array assignment, the length must be adapted too
        if is_variable_array(assignment_target_variable):
            assignment_value_type = assignment_value.get_expression_type()
            if assignment_value_type is JaniExpressionType.OPERATOR:
                assert is_expression_array(
                    assignment_value
                ), "Array variables must be assigned array expressions."
                value_array_length = len(
                    string_to_value(assign_expr, assignment_target_variable.get_type())
                )
            else:
                assert assignment_value_type is JaniExpressionType.IDENTIFIER
                value_array_length = JaniExpression(f"{assignment_value.as_identifier()}.length")
            assignments.append(
                JaniAssignment(
                    {
                        "ref": f"{assignment_target_id}.length",
                        "value": value_array_length,
                        "index": assign_index,
                    }
                )
            )
    return assignments


def generate_jani_variable(var_name: str, var_type: ValidTypes, array_size: int):
    """Helper to make a JaniVariable object."""
    # TODO: Move it to jani_utils.py
    if is_array_type(var_type):
        array_type = get_args(var_type)[0]
        init_value = array_create_operator("__array_iterator", array_size, array_type(0))
    else:
        init_value = JaniExpression(get_default_expression_for_type(var_type))
    return JaniVariable(var_name, var_type, init_value)
