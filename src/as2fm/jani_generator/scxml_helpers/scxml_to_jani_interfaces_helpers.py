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
Helper functions used in `as2fm.jani_generator.scxml_helpers.scxml_to_jani_interfaces`.
"""

from hashlib import sha256
from typing import Any, Dict, List, Optional, Tuple, Union

import lxml.etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.common import SupportedECMAScriptSequences, value_to_type
from as2fm.as2fm_common.ecmascript_interpretation import interpret_ecma_script_expr
from as2fm.as2fm_common.logging import get_error_msg
from as2fm.jani_generator.jani_entries import (
    JaniAssignment,
    JaniAutomaton,
    JaniEdge,
    JaniExpression,
    JaniExpressionType,
    JaniGuard,
    JaniVariable,
)
from as2fm.jani_generator.jani_entries.jani_expression_generator import (
    and_operator,
    max_operator,
    not_operator,
    plus_operator,
)
from as2fm.jani_generator.jani_entries.jani_utils import (
    generate_jani_variable,
    get_array_variable_info,
    is_expression_array,
    is_variable_array,
)
from as2fm.jani_generator.scxml_helpers.scxml_event import Event, EventsHolder
from as2fm.jani_generator.scxml_helpers.scxml_expression import (
    ArrayInfo,
    parse_ecmascript_to_jani_expression,
)
from as2fm.scxml_converter.scxml_entries import (
    ScxmlAssign,
    ScxmlBase,
    ScxmlExecutionBody,
    ScxmlIf,
    ScxmlSend,
)


def generate_jani_assignments(
    target_expr: Union[JaniExpression, JaniVariable],
    assign_expr: str,
    context_vars: Dict[str, JaniVariable],
    event_substitution: Optional[str],
    assign_index: int,
    elem_xml: XmlElement,
) -> List[JaniAssignment]:
    """
    Interpret SCXML assign element.

    :param target_expr: The expression to assign to the target expression.
    :param assign_expr: The target expression, recipient of the target_expr.
    :param context_vars: Context variables, used to evaluate the target_expr.
    :param event_substitution: The event that is associated to the provided expression (if any).
    :param assign_index: Priority index, to order the generated assignments.
    :param elem_xml: The XML element this assignment originates from.
    """
    assignments: List[JaniAssignment] = []
    if isinstance(target_expr, JaniExpression):
        target_expr_type = target_expr.get_expression_type()
    else:
        assert isinstance(target_expr, JaniVariable), get_error_msg(
            elem_xml, f"target_expr is {type(target_expr)} != (JaniExpression, JaniVariable)"
        )
        target_expr_type = JaniExpressionType.IDENTIFIER
    # An assignment target must be either a variable or a single array entry
    if target_expr_type is JaniExpressionType.OPERATOR:
        # If here, the target expression must be an array access (aa) operator
        assign_op_name, assign_operands = target_expr.as_operator()
        assert assign_op_name == "aa", get_error_msg(
            elem_xml, f"Unexpected assignment target: {assign_op_name} != 'aa'."
        )
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
        if isinstance(target_expr, JaniVariable):
            assignment_target_var = target_expr
        else:
            assignment_target_var = context_vars.get(target_expr.as_identifier())
            assert assignment_target_var is not None, get_error_msg(
                elem_xml,
                f"Variable {target_expr.as_identifier()} not in provided context {context_vars}.",
            )
        assignment_target_id = assignment_target_var.name()

        array_info = None
        if is_variable_array(assignment_target_var):
            array_info = ArrayInfo(*get_array_variable_info(assignment_target_var))
        assignment_value = parse_ecmascript_to_jani_expression(
            assign_expr, elem_xml, array_info
        ).replace_event(event_substitution)
        assignments.append(
            JaniAssignment(
                {"ref": assignment_target_id, "value": assignment_value, "index": assign_index}
            )
        )
        # In case this is an array assignment, the length must be adapted too
        if is_variable_array(assignment_target_var):
            assignment_value_type = assignment_value.get_expression_type()
            if assignment_value_type is JaniExpressionType.OPERATOR:
                assert is_expression_array(assignment_value), get_error_msg(
                    elem_xml, "Array variables must be assigned array expressions."
                )
                interpreted_expr = interpret_ecma_script_expr(assign_expr)
                assert isinstance(interpreted_expr, SupportedECMAScriptSequences), get_error_msg(
                    elem_xml,
                    f"Expected an array as interpretation result, got {type(interpreted_expr)}.",
                )
                value_array_length = len(interpreted_expr)
            else:
                assert assignment_value_type is JaniExpressionType.IDENTIFIER, get_error_msg(
                    elem_xml, "Expected an Identifier expression."
                )
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


def hash_element(element: Union[XmlElement, ScxmlBase, List[str]]) -> str:
    """
    Hash an ElementTree element.
    :param element: The element to hash.
    :return: The hash of the element.
    """
    if isinstance(element, XmlElement):
        s = ET.tostring(element, encoding="utf-8", method="xml")
    elif isinstance(element, ScxmlBase):
        s = ET.tostring(element.as_xml(), encoding="utf-8", method="xml")
    elif isinstance(element, list):
        s = ("/".join(f"{element}")).encode()
    else:
        raise ValueError(f"Element type {type(element)} not supported.")
    return sha256(s).hexdigest()[:8]


def _interpret_scxml_assign(
    elem: ScxmlAssign,
    jani_automaton: JaniAutomaton,
    event_substitution: Optional[str] = None,
    assign_index: int = 0,
) -> List[JaniAssignment]:
    """Interpret SCXML assign element.

    :param element: The SCXML element to interpret.
    :param jani_automaton: The Jani automaton related to the current scxml. Used for variable types.
    :param event_substitution: The event to substitute in the expression.
    :return: The action or expression to be executed.
    """
    assert isinstance(elem, ScxmlAssign), f"Expected ScxmlAssign, got {type(elem)}"
    assignment_target = parse_ecmascript_to_jani_expression(
        elem.get_location(), elem.get_xml_origin()
    )
    assign_expr = elem.get_expr()
    assert isinstance(assign_expr, str), get_error_msg(
        elem.get_xml_origin(), "Error: expected plain-scxml here."
    )

    return generate_jani_assignments(
        assignment_target,
        assign_expr,
        jani_automaton.get_variables(),
        event_substitution,
        assign_index,
        elem.get_xml_origin(),
    )


def merge_conditions(
    previous_conditions: Optional[List[JaniExpression]],
    new_condition: Optional[JaniExpression] = None,
) -> JaniExpression:
    """This merges negated conditions of previous if-clauses with the condition of the current
    if-clause. This is necessary to properly implement the if-else semantics of SCXML by parallel
    outgoing transitions in Jani.

    :param previous_conditions: The conditions of the previous if-clauses. (not yet negated)
    :param new_condition: The condition of the current if-clause.
    :return: The merged condition.
    """
    if new_condition is not None:
        joint_condition = new_condition
    else:
        joint_condition = JaniExpression(True)
    if previous_conditions is not None:
        for pc in previous_conditions:
            negated_pc = not_operator(pc)
            joint_condition = and_operator(joint_condition, negated_pc)
    return joint_condition


def append_scxml_body_to_jani_edge(
    jani_edge: JaniEdge,
    jani_automaton: JaniAutomaton,
    events_holder: EventsHolder,
    datamodel_vars: Dict[str, Any],
    body: ScxmlExecutionBody,
    target: str,
    probability: float,
    hash_str: str,
    data_event: Optional[str],
    max_array_size: int,
) -> Tuple[List[JaniEdge], List[str]]:
    """
    Converts the body of an SCXML element to a JaniDestination and appends it to an existing edge.

    Additional edges and location generated during conversion are provided in the returned tuple.
    They need to be added to a JaniAutomaton later on.

    :param jani_edge: An existing edge, where the generated JaniDestination will be appended.
    :param jani_automaton: The single automaton hosting the the existing edges and locations.
    :param events_holder: A data structure describing the events generated in the automaton.
    :param body: A list of SCXML entries to be translated into Jani.
    :param target: The location we are ending up in after executing the body.
    :param probability: The probability to pick this new destination.
    :param hash_str: Additional hash to ensure a unique action identifier to executing the body.
    :param data_event: The event carrying the data, that might be read in the exec block.
    :param max_array_size: The maximum allowed array size (for unbounded arrays).
    """
    additional_edges: List[JaniEdge] = []
    additional_locations: List[str] = []
    # Add necessary information to provided edge
    jani_edge.append_destination(probability=JaniExpression(probability))
    original_source = jani_edge.location
    # Reference to the latest created edge
    last_edge = jani_edge
    for i, ec in enumerate(body):
        intermediate_location = f"{original_source}-{hash_str}-{i}"
        if isinstance(ec, ScxmlAssign):
            assign_idx = len(last_edge.destinations[-1]["assignments"])
            jani_assigns = _interpret_scxml_assign(ec, jani_automaton, data_event, assign_idx)
            last_edge.destinations[-1]["assignments"].extend(jani_assigns)
        elif isinstance(ec, ScxmlSend):
            event_name = ec.get_event()
            event_send_action_name = event_name + "_on_send"
            last_edge.destinations[-1]["location"] = intermediate_location
            last_edge = JaniEdge(
                {
                    "location": intermediate_location,
                    "action": event_send_action_name,
                    "guard": None,
                }
            )
            new_edge_dest_assignments: List[JaniAssignment] = []
            data_structure_for_event: Dict[str, type] = {}
            for param in ec.get_params():
                param_assign_name = f"{ec.get_event()}.{param.get_name()}"
                expr = param.get_expr_or_location()
                # Update the events holder
                # TODO: get the expected type from a jani expression, w/o setting dummy values
                # TODO: expr might contain reference to event variables, that have no type specified
                # For now, we avoid the problem by using support variables in the model...
                # See https://github.com/convince-project/AS2FM/issues/84
                res_eval_value = interpret_ecma_script_expr(expr, datamodel_vars)
                res_eval_type = value_to_type(res_eval_value)
                data_structure_for_event[param.get_name()] = res_eval_type
                param_variable = generate_jani_variable(
                    param_assign_name, res_eval_type, max_array_size
                )
                new_edge_dest_assignments.extend(
                    generate_jani_assignments(
                        param_variable,
                        expr,
                        jani_automaton.get_variables(),
                        data_event,
                        0,
                        param.get_xml_origin(),
                    )
                )
            new_edge_dest_assignments.append(
                JaniAssignment({"ref": f"{ec.get_event()}.valid", "value": True})
            )

            if not events_holder.has_event(event_name):
                send_event = Event(event_name, data_structure_for_event)
                events_holder.add_event(send_event)
            else:
                send_event = events_holder.get_event(event_name)
                send_event.set_data_structure(data_structure_for_event)
            send_event.add_sender_edge(jani_automaton.get_name(), event_send_action_name)
            last_edge.append_destination(assignments=new_edge_dest_assignments)
            additional_edges.append(last_edge)
            additional_locations.append(intermediate_location)
        elif isinstance(ec, ScxmlIf):
            interm_loc_before = f"{intermediate_location}_before_if"
            interm_loc_after = f"{intermediate_location}_after_if"
            last_edge.destinations[-1]["location"] = interm_loc_before
            previous_conditions: List[JaniExpression] = []
            for if_idx, (cond_str, conditional_body) in enumerate(ec.get_conditional_executions()):
                current_cond = parse_ecmascript_to_jani_expression(cond_str, ec.get_xml_origin())
                jani_cond = merge_conditions(previous_conditions, current_cond).replace_event(
                    data_event
                )
                sub_edges, sub_locs = append_scxml_body_to_jani_automaton(
                    jani_automaton,
                    events_holder,
                    datamodel_vars,
                    conditional_body,
                    interm_loc_before,
                    interm_loc_after,
                    "-".join([hash_str, hash_element(ec), str(if_idx)]),
                    jani_cond,
                    None,  # This is not triggered by an event, even under a transition. Because
                    # the event triggering the transition is handled at the top of this function.
                    data_event,
                    max_array_size,
                )
                additional_edges.extend(sub_edges)
                additional_locations.extend(sub_locs)
                previous_conditions.append(current_cond)
            # Add else branch: if no else is provided, we assume an empty else body!
            else_execution_body = ec.get_else_execution()
            else_execution_id = str(len(ec.get_conditional_executions()))
            else_execution_body = [] if else_execution_body is None else else_execution_body
            jani_cond = merge_conditions(previous_conditions).replace_event(data_event)
            sub_edges, sub_locs = append_scxml_body_to_jani_automaton(
                jani_automaton,
                events_holder,
                datamodel_vars,
                ec.get_else_execution(),
                interm_loc_before,
                interm_loc_after,
                "-".join([hash_str, hash_element(ec), else_execution_id]),
                jani_cond,
                None,
                data_event,
                max_array_size,
            )
            additional_edges.extend(sub_edges)
            additional_locations.extend(sub_locs)
            # Prepare the edge from the end of the if-else block
            end_edge_action_name = f"{original_source}-{target}-{hash_str}"
            last_edge = JaniEdge(
                {
                    "location": interm_loc_after,
                    "action": end_edge_action_name,
                    "guard": None,
                    "destinations": [{"location": None, "assignments": []}],
                }
            )
            additional_edges.append(last_edge)
            additional_locations.append(interm_loc_before)
            additional_locations.append(interm_loc_after)
    last_edge.destinations[-1]["location"] = target
    return additional_edges, additional_locations


def append_scxml_body_to_jani_automaton(
    jani_automaton: JaniAutomaton,
    events_holder: EventsHolder,
    datamodel_vars: Dict[str, Any],
    body: ScxmlExecutionBody,
    source: str,
    target: str,
    hash_str: str,
    guard_exp: Optional[JaniExpression],
    trigger_event: Optional[str],
    data_event: Optional[str],
    max_array_size: int,
) -> Tuple[List[JaniEdge], List[str]]:
    """
    Converts the body of an SCXML element to a set of locations and edges.

    They need to be added to a JaniAutomaton later on.

    :param jani_automaton: The single automaton hosting the generated edges and locations.
    :param events_holder: A data structure describing the events generated in the automaton.
    :param body: A list of SCXML entries to be translated into Jani.
    :param source: The location we are starting executing the body from.
    :param target: The location we are ending up in after executing the body.
    :param hash_str: Additional hash to ensure a unique action identifier to executing the body.
    :param guard_exp: An expression that needs to hold before executing this action.
    :param trigger_event: The event starting the exec. block (use only from ScxmlTransition).
    :param data_event: The event carrying the data, that might be read in the exec block.
    :param max_array_size: The maximum allowed array size (for unbounded arrays).
    """
    jani_action_name = (
        f"{trigger_event}_on_receive"
        if trigger_event is not None
        else f"{source}-{target}-parent-{hash_str}"
    )

    if guard_exp is not None:
        guard_exp.replace_event(data_event)
    # First edge. Has to evaluate guard and trigger event of original transition.
    start_edge = JaniEdge(
        {
            "location": source,
            "action": jani_action_name,
            "guard": JaniGuard(guard_exp),
        }
    )
    additional_edges, additional_locations = append_scxml_body_to_jani_edge(
        start_edge,
        jani_automaton,
        events_holder,
        datamodel_vars,
        body,
        target,
        1.0,
        hash_str,
        data_event,
        max_array_size,
    )
    # Add the start_edge, since it is also automatically generated in this function
    return [start_edge] + additional_edges, additional_locations
