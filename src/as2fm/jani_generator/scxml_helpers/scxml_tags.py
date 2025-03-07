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

"""
Module defining SCXML tags to match against.
"""

from array import ArrayType, array
from hashlib import sha256
from typing import Any, Dict, List, MutableSequence, Optional, Set, Tuple, Union, get_args

import lxml.etree as ET
from lxml.etree import _Element as Element

from as2fm.as2fm_common.common import (
    EPSILON,
    check_value_type_compatible,
    get_default_expression_for_type,
    string_to_value,
    value_to_type,
)
from as2fm.as2fm_common.ecmascript_interpretation import interpret_ecma_script_expr
from as2fm.jani_generator.jani_entries import (
    JaniAssignment,
    JaniAutomaton,
    JaniEdge,
    JaniExpression,
    JaniExpressionType,
    JaniGuard,
    JaniValue,
    JaniVariable,
)
from as2fm.jani_generator.jani_entries.jani_expression_generator import (
    and_operator,
    max_operator,
    not_operator,
    plus_operator,
)
from as2fm.jani_generator.jani_entries.jani_utils import (
    get_all_variables_and_instantiations,
    get_array_type_and_size,
    get_variable_type,
    is_variable_array,
)
from as2fm.jani_generator.scxml_helpers.scxml_event import Event, EventsHolder, is_event_synched
from as2fm.jani_generator.scxml_helpers.scxml_expression import (
    ArrayInfo,
    parse_ecmascript_to_jani_expression,
)
from as2fm.scxml_converter.bt_converter import is_bt_root_scxml
from as2fm.scxml_converter.scxml_entries import (
    ScxmlAssign,
    ScxmlBase,
    ScxmlData,
    ScxmlDataModel,
    ScxmlExecutionBody,
    ScxmlIf,
    ScxmlRoot,
    ScxmlSend,
    ScxmlState,
    ScxmlTransition,
    ScxmlTransitionTarget,
)

# The resulting types from the SCXML conversion to Jani
ModelTupleType = Tuple[JaniAutomaton, EventsHolder]


def _hash_element(element: Union[Element, ScxmlBase, List[str]]) -> str:
    """
    Hash an ElementTree element.
    :param element: The element to hash.
    :return: The hash of the element.
    """
    if isinstance(element, Element):
        s = ET.tostring(element, encoding="utf-8", method="xml")
    elif isinstance(element, ScxmlBase):
        s = ET.tostring(element.as_xml(), encoding="utf-8", method="xml")
    elif isinstance(element, list):
        s = ("/".join(f"{element}")).encode()
    else:
        raise ValueError(f"Element type {type(element)} not supported.")
    return sha256(s).hexdigest()[:8]


def _convert_string_to_int_array(value: str) -> MutableSequence[int]:
    """
    Convert a string to a list of integers.
    """
    return array("i", [int(x) for x in value.encode()])


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
    assignment_target = parse_ecmascript_to_jani_expression(elem.get_location())
    target_expr_type = assignment_target.get_expression_type()
    is_target_array = target_expr_type == JaniExpressionType.IDENTIFIER and is_variable_array(
        jani_automaton, assignment_target.as_identifier()
    )
    array_info = None
    if is_target_array:
        var_info = get_array_type_and_size(jani_automaton, assignment_target.as_identifier())
        array_info = ArrayInfo(*var_info)
    # Check if the target is an array, in case copy the length too
    assignment_value = parse_ecmascript_to_jani_expression(
        elem.get_expr(), array_info
    ).replace_event(event_substitution)
    assignments: List[JaniAssignment] = [
        JaniAssignment({"ref": assignment_target, "value": assignment_value, "index": assign_index})
    ]
    # Handle array types
    if is_target_array:
        target_identifier = assignment_target.as_identifier()
        # We are assigning a new value to a complete array. We need to update the length too
        value_expr_type = assignment_value.get_expression_type()
        if value_expr_type == JaniExpressionType.IDENTIFIER:
            # Copy one array into another: simply copy the length from the source to the target
            value_identifier = assignment_value.as_identifier()
            assignments.append(
                JaniAssignment(
                    {
                        "ref": f"{target_identifier}.length",
                        "value": JaniExpression(f"{value_identifier}.length"),
                        "index": assign_index,
                    }
                )
            )
        elif value_expr_type == JaniExpressionType.OPERATOR:
            # Explicit array assignment: set the new length of the variable, too
            # This makes sense only if the operator is of type "av" (array value)
            op_type, operands = assignment_value.as_operator()
            assert (
                op_type == "av"
            ), f"Array assignment expects an array value (av) operator, found {op_type}."
            array_length = len(
                string_to_value(
                    elem.get_expr(), get_variable_type(jani_automaton, target_identifier)
                )
            )
            assignments.append(
                JaniAssignment(
                    {
                        "ref": f"{target_identifier}.length",
                        "value": JaniValue(array_length),
                        "index": assign_index,
                    }
                )
            )
        else:
            raise ValueError(
                f"Cannot assign expression {elem.get_expr()} to the array {target_identifier}."
            )
    elif target_expr_type == JaniExpressionType.OPERATOR:
        op_type, operands = assignment_target.as_operator()
        if op_type == "aa":
            # We are dealing with an array assignment. Update the length too
            array_name = operands["exp"].as_identifier()
            assert array_name is not None, "Array assignments expects an array identifier exp."
            array_length_id = f"{array_name}.length"
            array_idx = operands["index"]
            # Note: we do not make sure the max length increase is 1 (that is our assumption)
            # One way to do it could be to set the array length to -1 in case of broken assumptions
            new_length = max_operator(plus_operator(array_idx, 1), array_length_id)
            assignments.append(
                JaniAssignment({"ref": array_length_id, "value": new_length, "index": assign_index})
            )
    return assignments


def _merge_conditions(
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


def _append_scxml_body_to_jani_edge(
    jani_edge: JaniEdge,
    jani_automaton: JaniAutomaton,
    events_holder: EventsHolder,
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
            new_edge_dest_assignments: List[ScxmlAssign] = []
            data_structure_for_event: Dict[str, type] = {}
            for param in ec.get_params():
                param_assign_name = f"{ec.get_event()}.{param.get_name()}"
                expr = param.get_expr_or_location()
                # Update the events holder
                # TODO: get the expected type from a jani expression, w/o setting dummy values
                variables = get_all_variables_and_instantiations(jani_automaton)
                # TODO: This might contain reference to event variables, that have no type specified
                # For now, we avoid the problem by using support variables in the model...
                # See https://github.com/convince-project/AS2FM/issues/84
                res_eval_value = interpret_ecma_script_expr(expr, variables)
                # Special handling for strings...
                if isinstance(res_eval_value, str):
                    res_eval_value = _convert_string_to_int_array(res_eval_value)
                res_eval_type = value_to_type(res_eval_value)
                data_structure_for_event[param.get_name()] = res_eval_type
                array_info = None
                if isinstance(res_eval_value, ArrayType):
                    array_info = ArrayInfo(get_args(res_eval_type)[0], max_array_size)
                jani_expr = parse_ecmascript_to_jani_expression(expr, array_info).replace_event(
                    data_event
                )
                new_edge_dest_assignments.append(
                    JaniAssignment({"ref": param_assign_name, "value": jani_expr})
                )
                # TODO: Try to reuse as much as possible from _interpret_scxml_assign
                # If we are sending an array, set the length as well
                jani_expr_type = jani_expr.get_expression_type()
                if jani_expr_type == JaniExpressionType.IDENTIFIER:
                    variable_name = jani_expr.as_identifier()
                    if is_variable_array(jani_automaton, variable_name):
                        new_edge_dest_assignments.append(
                            JaniAssignment(
                                {
                                    "ref": f"{param_assign_name}.length",
                                    "value": f"{variable_name}.length",
                                }
                            )
                        )
                elif jani_expr_type == JaniExpressionType.OPERATOR:
                    op_type, _ = jani_expr.as_operator()
                    if op_type == "av":
                        assert isinstance(
                            res_eval_value, ArrayType
                        ), f"Expected array value, got {res_eval_value}."
                        new_edge_dest_assignments.append(
                            JaniAssignment(
                                {
                                    "ref": f"{param_assign_name}.length",
                                    "value": JaniValue(len(res_eval_value)),
                                }
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
                current_cond = parse_ecmascript_to_jani_expression(cond_str)
                jani_cond = _merge_conditions(previous_conditions, current_cond).replace_event(
                    data_event
                )
                sub_edges, sub_locs = _append_scxml_body_to_jani_automaton(
                    jani_automaton,
                    events_holder,
                    conditional_body,
                    interm_loc_before,
                    interm_loc_after,
                    "-".join([hash_str, _hash_element(ec), str(if_idx)]),
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
            jani_cond = _merge_conditions(previous_conditions).replace_event(data_event)
            sub_edges, sub_locs = _append_scxml_body_to_jani_automaton(
                jani_automaton,
                events_holder,
                ec.get_else_execution(),
                interm_loc_before,
                interm_loc_after,
                "-".join([hash_str, _hash_element(ec), else_execution_id]),
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


def _append_scxml_body_to_jani_automaton(
    jani_automaton: JaniAutomaton,
    events_holder: EventsHolder,
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
    additional_edges, additional_locations = _append_scxml_body_to_jani_edge(
        start_edge,
        jani_automaton,
        events_holder,
        body,
        target,
        1.0,
        hash_str,
        data_event,
        max_array_size,
    )
    # Add the start_edge, since it is also automatically generated in this function
    return [start_edge] + additional_edges, additional_locations


class BaseTag:
    """Base class for all SCXML tags."""

    # class function to initialize the correct tag object
    @staticmethod
    def from_element(
        element: ScxmlBase, call_trace: List[ScxmlBase], model: ModelTupleType, max_array_size: int
    ) -> "BaseTag":
        """Return the correct tag object based on the xml element.

        :param element: The xml element representing the tag.
        :param call_trace: The call trace of the element, to access the parents.
        :param model: The model to write the tag to.
        :param max_array_size: The maximum index of the arrays in the model.
        :return: The corresponding tag object.
        """
        if type(element) not in CLASS_BY_TYPE:
            raise NotImplementedError(f"Support for SCXML type >{type(element)}< not implemented.")
        return CLASS_BY_TYPE[type(element)](element, call_trace, model, max_array_size)

    def __init__(
        self,
        element: ScxmlBase,
        call_trace: List[ScxmlBase],
        model: ModelTupleType,
        max_array_size: int,
    ) -> None:
        """Initialize the ScxmlTag object from an xml element.

        :param element: The xml element representing the tag.
        :param call_trace: The call trace of the element, to access the parents.
        :param model: The model to write the tag to.
        :param max_array_size: The maximum index of the arrays in the model.
        """
        self.max_array_size = max_array_size
        self.element = element
        self.automaton, self.events_holder = model
        self.call_trace = call_trace
        scxml_children = self.get_children()
        self.children = [
            BaseTag.from_element(child, call_trace + [element], model, max_array_size)
            for child in scxml_children
        ]

    def get_children(
        self,
    ) -> Union[List[ScxmlBase], List[ScxmlTransition], List[Union[ScxmlDataModel, ScxmlState]]]:
        """Method extracting all children from a specific Scxml Tag."""
        raise NotImplementedError("Method get_children not implemented.")

    def get_tag_name(self) -> str:
        """Return the tag name to match against."""
        return self.element.get_tag_name()

    def write_model(self):
        """Return the model of the tag.

        :return: The model of the tag.
        """
        for child in self.children:
            child.write_model()


class DatamodelTag(BaseTag):
    """Object representing a datamodel tag from a SCXML file.

    See https://www.w3.org/TR/scxml/#datamodel
    """

    def get_children(self) -> List[ScxmlBase]:
        return []

    def write_model(self):
        # A collection of the variables read from the datamodel so far
        read_vars: Dict[str, Any] = {}
        for scxml_data in self.element.get_data_entries():
            assert isinstance(scxml_data, ScxmlData), "Unexpected element in the DataModel."
            assert scxml_data.check_validity(), "Found invalid data entry."
            # TODO: ScxmlData from scxml_helpers provide many more options.
            # It should be ported to scxml_entries.ScxmlDataModel
            expected_type = scxml_data.get_type()
            array_info: Optional[ArrayInfo] = None
            if expected_type not in (int, float, bool, str):
                # Not a basic type: we are dealing with an array
                array_type = get_args(expected_type)[0]
                assert array_type in (int, float), f"Type {expected_type} not supported in arrays."
                max_array_size = scxml_data.get_array_max_size()
                if max_array_size is None:
                    max_array_size = self.max_array_size
                expected_type = ArrayType
                array_info = ArrayInfo(array_type, max_array_size)
            init_value = parse_ecmascript_to_jani_expression(scxml_data.get_expr(), array_info)
            evaluated_expr = interpret_ecma_script_expr(scxml_data.get_expr(), read_vars)
            assert check_value_type_compatible(evaluated_expr, expected_type), (
                f"Invalid value for {scxml_data.get_name()}: "
                f"Expected type {expected_type}, got {type(evaluated_expr)}."
            )
            # Special case for strings: treat them as array of integers
            if isinstance(evaluated_expr, str):
                expected_type = MutableSequence[int]
            # TODO: Add support for lower and upper bounds
            self.automaton.add_variable(
                JaniVariable(scxml_data.get_name(), expected_type, init_value)
            )
            # In case of arrays, declare an additional 'length' variable
            # In this case, use dot notation, as in JS arrays
            if expected_type is ArrayType:
                init_expr = string_to_value(scxml_data.get_expr(), expected_type)
                # TODO: The length variable NEEDS to be bounded
                self.automaton.add_variable(
                    JaniVariable(f"{scxml_data.get_name()}.length", int, JaniValue(len(init_expr)))
                )
            read_vars.update(
                {scxml_data.get_name(): get_default_expression_for_type(expected_type)}
            )


class ScxmlTag(BaseTag):
    """Object representing the root SCXML tag."""

    def get_children(self) -> List[Union[ScxmlDataModel, ScxmlState]]:
        root_children = []
        data_model = self.element.get_data_model()
        if data_model is not None:
            root_children.append(data_model)
        root_children.extend(self.element.get_states())
        return root_children

    def handle_entry_state(self):
        """Get the entry state and mark it in the Jani Automaton.

        If the entry state has an onentry block, generate a new entry sequence and add it to Jani.
        """
        # Note: we don't support the initial tag (as state) https://www.w3.org/TR/scxml/#initial
        initial_state_id = self.element.get_initial_state_id()
        initial_state = self.element.get_state_by_id(initial_state_id)
        # Make sure we execute the onentry block of the initial state at the start
        if len(initial_state.get_onentry()) > 0:
            source_state = f"{initial_state_id}-first-exec"
            target_state = initial_state_id
            onentry_body = initial_state.get_onentry()
            hash_str = _hash_element([source_state, target_state, "onentry"])
            new_edges, new_locations = _append_scxml_body_to_jani_automaton(
                self.automaton,
                self.events_holder,
                onentry_body,
                source_state,
                target_state,
                hash_str,
                None,
                None,
                None,
                self.max_array_size,
            )
            # Add the initial state and start sequence to the automaton
            self.automaton.add_location(source_state)
            self.automaton.make_initial(source_state)
            for edge in new_edges:
                self.automaton.add_edge(edge)
            for loc in new_locations:
                self.automaton.add_location(loc)
        else:
            self.automaton.make_initial(initial_state_id)

    def add_unhandled_transitions(self):
        """Add self-loops in each state for transitions that weren't handled yet."""
        if is_bt_root_scxml(self.element.get_name()):
            # The autogenerated BT Root should have no autogenerated empty self-loop.
            # This prevents the global timer to advance uncontrolled without the BT being ticked
            return
        transitions_set = set()
        for child in self.children:
            if isinstance(child, StateTag):
                transitions_set = transitions_set.union(child.get_handled_events())
        for child in self.children:
            if isinstance(child, StateTag):
                child.add_unhandled_transitions(transitions_set)

    def write_model(self):
        assert isinstance(self.element, ScxmlRoot), f"Expected ScxmlRoot, got {type(self.element)}."
        self.automaton.set_name(self.element.get_name())
        super().write_model()
        self.add_unhandled_transitions()
        self.handle_entry_state()


class StateTag(BaseTag):
    """Object representing a state tag from a SCXML file.

    See https://www.w3.org/TR/scxml/#state
    """

    def get_children(self) -> List[ScxmlTransition]:
        # Here we care only about the transitions.
        # onentry and onexit are handled in the TransitionTag
        state_transitions = self.element.get_body()
        return [] if state_transitions is None else state_transitions

    def get_handled_events(self) -> Set[str]:
        """Return the events that are handled by the state."""
        transition_events = set(self._events_no_condition)
        for event_name in self._event_to_conditions.keys():
            transition_events.add(event_name)
        return transition_events

    def get_guard_exp_for_prev_conditions(self, event_name: str) -> Optional[JaniExpression]:
        """Return the guard negating all previous conditions for a specific event.

        This is required to make sure each event is processed, even in case of conditionals like:
        <transition event="a" cond="_event.X > 5" target="somewhere" />, that could result in a
        deadlock if the content of the event sent is not greater than 5.
        We want to automatically generate a "dummy" self-loop for that same event with the opposite
        condition(s), to cover the case where the self-loop is not met:
        <transition event="a" cond="_event.X <= 5" target="self" />
        """
        previous_expressions = [
            parse_ecmascript_to_jani_expression(cond)
            for cond in self._event_to_conditions.get(event_name, [])
        ]
        if len(previous_expressions) > 0:
            return _merge_conditions(previous_expressions)
        else:
            return None

    def add_unhandled_transitions(self, transitions_set: Set[str]):
        """Add self-loops for transitions that weren't handled yet."""
        for event_name in transitions_set:
            if not self._generate_empty_event_transitions:
                continue
            if event_name in self._events_no_condition or len(event_name) == 0:
                continue
            guard_exp = self.get_guard_exp_for_prev_conditions(event_name)
            # If the event was not handled in the state and is expected to be synched, skip it
            if guard_exp is None and is_event_synched(event_name):
                continue
            edges, locations = _append_scxml_body_to_jani_automaton(
                self.automaton,
                self.events_holder,
                [],
                self.element.get_id(),
                self.element.get_id(),
                "",
                guard_exp,
                event_name,
                event_name,
                self.max_array_size,
            )
            assert (
                len(locations) == 0 and len(edges) == 1
            ), f"Expected one edge for self-loops, got {len(edges)} edges."
            self.automaton.add_edge(edges[0])
            self._events_no_condition.append(event_name)

    def write_model(self):
        # Whether we should auto-generate empty self-loops for unhandled events
        has_event_transition: bool = False
        state_name = self.element.get_id()
        self.automaton.add_location(state_name)
        # Dictionary tracking the conditional trigger-based transitions
        self._event_to_conditions: Dict[str, List[str]] = {}
        # List of events that trigger transitions without conditions
        self._events_no_condition: List[str] = []
        for child in self.children:
            transition_events = child.element.get_events()
            assert len(transition_events) <= 1, "Multiple events in a transition not supported."
            if len(transition_events) == 0:
                transition_event: str = ""
            else:
                transition_event = transition_events[0]
                has_event_transition = True
            assert transition_event not in self._events_no_condition, (
                f"Event {transition_event} in state {self.element.get_id()} has already a base"
                "exit condition."
            )
            transition_condition = child.element.get_condition()
            # Add previous conditions matching the same event trigger to the current child state
            child.set_previous_siblings_conditions(
                self._event_to_conditions.get(transition_event, [])
            )
            # Write the model BEFORE appending the new condition to the events' conditions list
            child.write_model()
            if transition_condition is None:
                # Base condition for transitioning, when all previous aren't verified
                self._events_no_condition.append(transition_event)
            else:
                # Update the list of conditions related to a transition trigger
                if transition_event not in self._event_to_conditions:
                    self._event_to_conditions[transition_event] = []
                self._event_to_conditions[transition_event].append(transition_condition)
        # if "" in self._events_no_condition, then we can transition to new states without events
        assert not (has_event_transition and "" in self._events_no_condition), (
            f"Model {self.call_trace[0].get_name()} at state {self.element.get_id()} can always "
            "transition without an event trigger: not event-based transitions expected."
        )
        self._generate_empty_event_transitions = "" not in self._events_no_condition


class TransitionTag(BaseTag):
    """Object representing a transition tag from a SCXML file.

    See https://www.w3.org/TR/scxml/#transition
    """

    def get_children(self) -> List[ScxmlBase]:
        return []

    def set_previous_siblings_conditions(self, conditions_scripts: List[str]):
        """Add conditions from previous transitions with same event trigger."""
        self._previous_conditions = conditions_scripts

    def _get_event(self) -> Optional[str]:
        event_name = self.element.get_events()
        # TODO: Need to extend this to support multiple events
        assert len(event_name) <= 1, "Transitions triggered by multiple events are not supported."
        if len(event_name) == 0:
            return None
        assert len(event_name[0]) > 0, "Transition: empty event name not supported."
        return event_name[0]

    def write_model(self):
        assert hasattr(
            self, "_previous_conditions"
        ), "Make sure 'set_previous_siblings_conditions' was called before."
        # Current state
        scxml_root: ScxmlRoot = self.call_trace[0]
        current_state: ScxmlState = self.call_trace[-1]
        current_state_id: str = current_state.get_id()
        # Event processing (true for the whole transition)
        current_condition = self.element.get_condition()
        trigger_event = self._get_event()
        if trigger_event is not None:
            action_name = f"{trigger_event}_on_receive"
            if not self.events_holder.has_event(trigger_event):
                self.events_holder.add_event(
                    Event(
                        trigger_event
                        # The data structure can't be deducted here
                    )
                )
            existing_event = self.events_holder.get_event(trigger_event)
            existing_event.add_receiver(self.automaton.get_name(), action_name)
        else:
            eventless_hash = _hash_element([current_state_id, current_condition])
            action_name = f"transition-{current_state_id}-eventless-{eventless_hash}"
        transition_targets: List[ScxmlTransitionTarget] = self.element.get_targets()
        # Transition condition (guard) processing
        previous_conditions_expr = [
            parse_ecmascript_to_jani_expression(cond) for cond in self._previous_conditions
        ]
        current_condition_expr = None
        if current_condition is not None:
            current_condition_expr = parse_ecmascript_to_jani_expression(current_condition)
        if trigger_event is not None:
            for single_cond_expr in previous_conditions_expr:
                single_cond_expr.replace_event(trigger_event)
            if current_condition_expr is not None:
                current_condition_expr.replace_event(trigger_event)
        jani_guard = _merge_conditions(previous_conditions_expr, current_condition_expr)
        # Transition targets processing
        assert len(transition_targets) > 0, f"Transition with no target in {scxml_root.get_name()}."
        transition_edge = JaniEdge(
            {
                "location": current_state_id,
                "action": action_name,
                "guard": jani_guard,
            }
        )
        # Accumulate the various targets probabilities here
        total_probability = 0.0
        generated_edges: List[JaniEdge] = []
        generated_locations: List[str] = []
        for single_target in transition_targets:
            # target probability
            target_probability = single_target.get_probability()
            if target_probability is None:
                target_probability = 1.0 - total_probability
            assert (
                target_probability > 0.0
            ), f"Transition probability lower than 0: {target_probability}"
            total_probability += target_probability
            # target state
            target_state_id: str = single_target.get_target_id()
            target_state: ScxmlState = scxml_root.get_state_by_id(target_state_id)
            assert (
                target_state is not None
            ), f"Transition's target state {target_state_id} not found."
            # Prepare the transition body:
            original_transition_body = single_target.get_body()
            merged_transition_body = []
            if current_state.get_onexit() is not None:
                merged_transition_body.extend(current_state.get_onexit())
            merged_transition_body.extend(original_transition_body)
            if target_state.get_onentry() is not None:
                merged_transition_body.extend(target_state.get_onentry())
            # Generate this target's hash, add the total probability since differs for each target
            target_hash = _hash_element(
                [
                    current_state_id,
                    target_state_id,
                    action_name,
                    current_condition,
                    str(total_probability),
                ]
            )
            additional_edges, additional_locations = _append_scxml_body_to_jani_edge(
                transition_edge,
                self.automaton,
                self.events_holder,
                merged_transition_body,
                target_state_id,
                target_probability,
                target_hash,
                trigger_event,
                self.max_array_size,
            )
            generated_edges.extend(additional_edges)
            generated_locations.extend(additional_locations)
        assert (
            abs(1.0 - total_probability) <= EPSILON
        ), f"Transition total probability sums to {total_probability}. Must be 1.0."
        self.automaton.add_edge(transition_edge)
        for edge in generated_edges:
            self.automaton.add_edge(edge)
        for loc in generated_locations:
            self.automaton.add_location(loc)


CLASS_BY_TYPE = {
    ScxmlDataModel: DatamodelTag,
    ScxmlRoot: ScxmlTag,
    ScxmlState: StateTag,
    ScxmlTransition: TransitionTag,
}
