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

import xml.etree.ElementTree as ET
from hashlib import sha256
from typing import get_args, get_origin, Dict, List, MutableSequence, Optional, Set, Tuple, Union

from as2fm_common.common import (
    check_value_type_compatible, get_default_expression_for_type, string_to_value, value_to_type)
from as2fm_common.ecmascript_interpretation import interpret_ecma_script_expr
from jani_generator.jani_entries import (
    JaniAssignment, JaniAutomaton, JaniEdge, JaniExpression, JaniExpressionType, JaniGuard,
    JaniValue, JaniVariable)
from jani_generator.jani_entries.jani_expression_generator import (
    and_operator, not_operator, max_operator, plus_operator)
from jani_generator.scxml_helpers.scxml_event import Event, EventsHolder
from jani_generator.scxml_helpers.scxml_expression import (
    ArrayInfo, parse_ecmascript_to_jani_expression)
from scxml_converter.scxml_entries import (ScxmlAssign, ScxmlBase, ScxmlData,
                                           ScxmlDataModel, ScxmlExecutionBody,
                                           ScxmlIf, ScxmlRoot, ScxmlSend,
                                           ScxmlState, ScxmlTransition)

# The resulting types from the SCXML conversion to Jani
ModelTupleType = Tuple[JaniAutomaton, EventsHolder]


def _hash_element(element: Union[ET.Element, ScxmlBase, List[str]]) -> str:
    """
    Hash an ElementTree element.
    :param element: The element to hash.
    :return: The hash of the element.
    """
    if isinstance(element, ET.Element):
        s = ET.tostring(element, encoding='unicode', method='xml')
    elif isinstance(element, ScxmlBase):
        s = ET.tostring(element.as_xml(), encoding='unicode', method='xml')
    elif isinstance(element, list):
        s = '/'.join(f"{element}")
    else:
        raise ValueError(f"Element type {type(element)} not supported.")
    return sha256(s.encode()).hexdigest()[:8]


def _get_variable_type(jani_automaton: JaniAutomaton, variable_name: Optional[str]) -> type:
    """
    Retrieve the variable type from the Jani automaton.

    :param jani_automaton: The Jani automaton to check the variable in.
    :param variable_name: The name of the variable to check.
    :return: The retrieved type.
    """
    assert variable_name is not None, "Variable name must be provided."
    variable = jani_automaton.get_variables().get(variable_name)
    assert variable is not None, \
        f"Variable {variable_name} not found in {jani_automaton.get_variables()}."
    return variable.get_type()


def _is_variable_array(jani_automaton: JaniAutomaton, variable_name: Optional[str]) -> bool:
    """Check if a variable is an array.

    :param jani_automaton: The Jani automaton to check the variable in.
    :param variable_name: The name of the variable to check.
    :return: True if the variable is an array, False otherwise.
    """
    return get_origin(_get_variable_type(jani_automaton, variable_name)) == \
        get_origin(MutableSequence)


def _get_array_info(jani_automaton: JaniAutomaton, var_name: str) -> ArrayInfo:
    """
    Generate the ArrayInfo obj. related to the provided variable.

    :param jani_automaton: The Jani automaton to get the variable from.
    :param var_name: The name of the variable to generate the info from.
    :return: The ArrayInfo obj. with array type and max size.
    """
    assert var_name is not None, "Variable name must be provided."
    variable = jani_automaton.get_variables().get(var_name)
    var_type = variable.get_type()
    assert get_origin(var_type) == get_origin(MutableSequence), \
        f"Variable {var_name} not an array, cannot extract array info."
    array_type = get_args(var_type)[0]
    assert array_type in (int, float), f"Array type {array_type} not supported."
    init_operator = variable.get_init_expr().as_operator()
    assert init_operator is not None, f"Expected init expr of {var_name} to be an operator expr."
    if init_operator[0] == "av":
        max_size = len(init_operator[1]['elements'].as_literal().value())
    elif init_operator[0] == "ac":
        max_size = init_operator[1]['length'].as_literal().value()
    else:
        raise ValueError(f"Unexpected operator {init_operator[0]} for {var_name} init expr.")
    return ArrayInfo(array_type, max_size)


def _interpret_scxml_assign(
        elem: ScxmlAssign, jani_automaton: JaniAutomaton, event_substitution: Optional[str] = None,
        assign_index: int = 0) -> List[JaniAssignment]:
    """Interpret SCXML assign element.

    :param element: The SCXML element to interpret.
    :param jani_automaton: The Jani automaton related to the current scxml. Used for variable types.
    :param event_substitution: The event to substitute in the expression.
    :return: The action or expression to be executed.
    """
    assert isinstance(elem, ScxmlAssign), \
        f"Expected ScxmlAssign, got {type(elem)}"
    assignment_target = parse_ecmascript_to_jani_expression(elem.get_location())
    target_expr_type = assignment_target.get_expression_type()
    is_target_array = target_expr_type == JaniExpressionType.IDENTIFIER and \
        _is_variable_array(jani_automaton, assignment_target.as_identifier())
    array_info = None
    if is_target_array:
        array_info = _get_array_info(jani_automaton, assignment_target.as_identifier())
    # Check if the target is an array, in case copy the length too
    assignment_value = parse_ecmascript_to_jani_expression(
        elem.get_expr(), array_info).replace_event(event_substitution)
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
            assignments.append(JaniAssignment({
                "ref": f"{target_identifier}.length",
                "value": JaniExpression(f"{value_identifier}.length")
            }))
        elif value_expr_type == JaniExpressionType.OPERATOR:
            # Explicit array assignment: set the new length of the variable, too
            # This makes sense only if the operator is of type "av" (array value)
            op_type, operands = assignment_value.as_operator()
            assert op_type == "av", \
                f"Array assignment expects an array value (av) operator, found {op_type}."
            array_length = len(string_to_value(
                elem.get_expr(), _get_variable_type(jani_automaton, target_identifier)))
            assignments.append(JaniAssignment({
                "ref": f"{target_identifier}.length",
                "value": JaniValue(array_length)
            }))
        else:
            raise ValueError(
                f"Cannot assign expression {elem.get_expr()} to the array {target_identifier}.")
    elif target_expr_type == JaniExpressionType.OPERATOR:
        op_type, operands = assignment_target.as_operator()
        if op_type == "aa":
            # We are dealing with an array assignment. Update the length too
            array_name = operands['exp'].as_identifier()
            assert array_name is not None, "Array assignments expects an array identifier exp."
            array_length_id = f"{array_name}.length"
            array_idx = operands['index']
            # Note: we do not make sure the max length increase is 1 (that is our assumption)
            # One way to do it could be to set the array length to -1 in case of broken assumptions
            new_length = max_operator(plus_operator(array_idx, 1), array_length_id)
            assignments.append(JaniAssignment({
                "ref": array_length_id,
                "value": new_length
            }))
    return assignments


def _merge_conditions(
        previous_conditions: List[JaniExpression],
        new_condition: Optional[JaniExpression] = None) -> JaniExpression:
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
    for pc in previous_conditions:
        negated_pc = not_operator(pc)
        joint_condition = and_operator(joint_condition, negated_pc)
    return joint_condition


def _append_scxml_body_to_jani_automaton(jani_automaton: JaniAutomaton, events_holder: EventsHolder,
                                         body: ScxmlExecutionBody, source: str, target: str,
                                         hash_str: str, guard_exp: Optional[JaniExpression],
                                         trigger_event: Optional[str]) \
        -> Tuple[List[JaniEdge], List[str]]:
    """
    Converts the body of an SCXML element to a set of locations and edges.

    They need to be added to a JaniAutomaton later on.
    """
    edge_action_name = f"{source}-{target}-{hash_str}"
    trigger_event_action = \
        edge_action_name if trigger_event is None else f"{trigger_event}_on_receive"
    new_edges = []
    new_locations = []
    if guard_exp is not None:
        guard_exp.replace_event(trigger_event)
    # First edge. Has to evaluate guard and trigger event of original transition.
    new_edges.append(JaniEdge({
        "location": source,
        "action": trigger_event_action,
        "guard": JaniGuard(guard_exp),
        "destinations": [{
            "location": None,
            "assignments": []
        }]
    }))
    for i, ec in enumerate(body):
        if isinstance(ec, ScxmlAssign):
            assign_idx = len(new_edges[-1].destinations[0]['assignments'])
            jani_assigns = _interpret_scxml_assign(ec, jani_automaton, trigger_event, assign_idx)
            new_edges[-1].destinations[0]['assignments'].extend(jani_assigns)
        elif isinstance(ec, ScxmlSend):
            event_name = ec.get_event()
            event_send_action_name = event_name + "_on_send"
            interm_loc = f'{source}-{i}-{hash_str}'
            new_edges[-1].destinations[0]['location'] = interm_loc
            new_edge = JaniEdge({
                "location": interm_loc,
                "action": event_send_action_name,
                "guard": None,
                "destinations": [{
                    "location": None,
                    "assignments": []
                }]
            })
            data_structure_for_event: Dict[str, type] = {}
            for param in ec.get_params():
                param_assign_name = f'{ec.get_event()}.{param.get_name()}'
                expr = param.get_expr() if param.get_expr() is not None else \
                    param.get_location()
                jani_expr = parse_ecmascript_to_jani_expression(expr).replace_event(trigger_event)
                new_edge.destinations[0]['assignments'].append(JaniAssignment({
                    "ref": param_assign_name,
                    "value": jani_expr
                }))
                # TODO: Try to reuse as much as possible from _interpret_scxml_assign
                # If we are sending an array, set the length as well
                if jani_expr.get_expression_type() == JaniExpressionType.IDENTIFIER:
                    variable_name = jani_expr.as_identifier()
                    if _is_variable_array(jani_automaton, variable_name):
                        new_edge.destinations[0]['assignments'].append(JaniAssignment({
                            "ref": f'{param_assign_name}.length',
                            "value": f"{variable_name}.length"}))
                # TODO: get the expected type from a jani expression, w/o setting dummy def. values
                variables = {}
                for n, v in jani_automaton.get_variables().items():
                    variables[n] = get_default_expression_for_type(v.get_type())
                    # Hack to solve issue for expressions with explicit access to array entries
                    if isinstance(variables[n], MutableSequence):
                        for _ in range(50):
                            variables[n].append(0)
                    # Another hack, since javascript interprets 0.0 as int...
                    if isinstance(variables[n], float):
                        variables[n] = 0.1
                # TODO: We should get the type explicitly: sometimes the expression is under-defined
                # This might contain reference to event variables, that have no type specified
                data_structure_for_event[param.get_name()] = value_to_type(
                    interpret_ecma_script_expr(expr, variables))
            new_edge.destinations[0]['assignments'].append(JaniAssignment({
                "ref": f'{ec.get_event()}.valid',
                "value": True
            }))

            if not events_holder.has_event(event_name):
                send_event = Event(
                    event_name,
                    data_structure_for_event
                )
                events_holder.add_event(send_event)
            else:
                send_event = events_holder.get_event(event_name)
                send_event.set_data_structure(
                    data_structure_for_event
                )
            send_event.add_sender_edge(jani_automaton.get_name(), event_send_action_name)

            new_edges.append(new_edge)
            new_locations.append(interm_loc)
        elif isinstance(ec, ScxmlIf):
            if_prefix = f"{source}_{hash_str}_{i}"
            interm_loc_before = f"{if_prefix}_before_if"
            interm_loc_after = f"{if_prefix}_after_if"
            new_edges[-1].destinations[0]['location'] = interm_loc_before
            previous_conditions: List[JaniExpression] = []
            for if_idx, (cond_str, conditional_body) in enumerate(ec.get_conditional_executions()):
                current_cond = parse_ecmascript_to_jani_expression(cond_str)
                jani_cond = _merge_conditions(
                    previous_conditions, current_cond).replace_event(trigger_event)
                sub_edges, sub_locs = _append_scxml_body_to_jani_automaton(
                    jani_automaton, events_holder, conditional_body, interm_loc_before,
                    interm_loc_after, '-'.join([hash_str, _hash_element(ec), str(if_idx)]),
                    jani_cond, None)
                new_edges.extend(sub_edges)
                new_locations.extend(sub_locs)
                previous_conditions.append(current_cond)
            # Add else branch: if no else is provided, we assume an empty else body!
            else_execution_body = ec.get_else_execution()
            else_execution_id = str(len(ec.get_conditional_executions()))
            else_execution_body = [] if else_execution_body is None else else_execution_body
            jani_cond = _merge_conditions(
                previous_conditions).replace_event(trigger_event)
            sub_edges, sub_locs = _append_scxml_body_to_jani_automaton(
                jani_automaton, events_holder, ec.get_else_execution(), interm_loc_before,
                interm_loc_after, '-'.join([hash_str, _hash_element(ec), else_execution_id]),
                jani_cond, None)
            new_edges.extend(sub_edges)
            new_locations.extend(sub_locs)
            # Prepare the edge from the end of the if-else block
            new_edges.append(JaniEdge({
                "location": interm_loc_after,
                "action": edge_action_name,
                "guard": None,
                "destinations": [{
                    "location": None,
                    "assignments": []
                }]
            }))
            new_locations.append(interm_loc_before)
            new_locations.append(interm_loc_after)
    new_edges[-1].destinations[0]['location'] = target
    return new_edges, new_locations


class BaseTag:
    """Base class for all SCXML tags."""
    # class function to initialize the correct tag object
    @staticmethod
    def from_element(element: ScxmlBase,
                     call_trace: List[ScxmlBase],
                     model: ModelTupleType,
                     max_array_size: int) -> 'BaseTag':
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

    def __init__(self, element: ScxmlBase,
                 call_trace: List[ScxmlBase],
                 model: ModelTupleType,
                 max_array_size: int) -> None:
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
            for child in scxml_children]

    def get_children(self) -> List[ScxmlBase]:
        """Method extracting all children from a specific Scxml Tag.
        """
        raise NotImplementedError("Method get_children not implemented.")

    def get_tag_name(self) -> str:
        """Return the tag name to match against.
        """
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
        for scxml_data in self.element.get_data_entries():
            assert isinstance(scxml_data, ScxmlData), "Unexpected element in the DataModel."
            assert scxml_data.check_validity(), "Found invalid data entry."
            # TODO: ScxmlData from scxml_helpers provide many more options.
            # It should be ported to scxml_entries.ScxmlDataModel
            expected_type = scxml_data.get_type()
            array_info: Optional[ArrayInfo] = None
            if expected_type not in (int, float, bool):
                # Not a basic type: we are dealing with an array
                array_type = get_args(expected_type)[0]
                assert array_type in (int, float), f"Type {expected_type} not supported in arrays."
                max_array_size = scxml_data.get_array_max_size()
                if max_array_size is None:
                    max_array_size = self.max_array_size
                expected_type = list
                array_info = ArrayInfo(array_type, max_array_size)
            init_value = parse_ecmascript_to_jani_expression(scxml_data.get_expr(), array_info)
            expr_type = type(interpret_ecma_script_expr(scxml_data.get_expr()))
            assert check_value_type_compatible(
                    interpret_ecma_script_expr(scxml_data.get_expr()), expected_type), \
                f"Invalid value for {scxml_data.get_name()}: " \
                f"Expected type {expected_type}, got {expr_type}."
            # TODO: Add support for lower and upper bounds
            self.automaton.add_variable(
                JaniVariable(scxml_data.get_name(), scxml_data.get_type(), init_value))
            # In case of arrays, declare an additional 'length' variable
            # In this case, use dot notation, as in JS arrays
            if expected_type is list:
                init_expr = string_to_value(scxml_data.get_expr(), scxml_data.get_type())
                # TODO: The length variable NEEDS to be bounded
                self.automaton.add_variable(
                    JaniVariable(f"{scxml_data.get_name()}.length", int, JaniValue(len(init_expr))))


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
                self.automaton, self.events_holder, onentry_body, source_state,
                target_state, hash_str, None, None)
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
        transitions_set = set()
        for child in self.children:
            if isinstance(child, StateTag):
                transitions_set = transitions_set.union(child.get_handled_events())
        for child in self.children:
            if isinstance(child, StateTag):
                child.add_unhandled_transitions(transitions_set)

    def write_model(self):
        assert isinstance(self.element, ScxmlRoot), \
            f"Expected ScxmlRoot, got {type(self.element)}."
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
        """Return the events that are handled by the state.
        """
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
            parse_ecmascript_to_jani_expression(cond) for
            cond in self._event_to_conditions.get(event_name, [])]
        if len(previous_expressions) > 0:
            return _merge_conditions(previous_expressions)
        else:
            return None

    def add_unhandled_transitions(self, transitions_set: Set[str]):
        """Add self-loops for transitions that weren't handled yet."""
        for event_name in transitions_set:
            if event_name in self._events_no_condition or len(event_name) == 0:
                continue
            guard_exp = self.get_guard_exp_for_prev_conditions(event_name)
            edges, locations = _append_scxml_body_to_jani_automaton(
                self.automaton, self.events_holder, [], self.element.get_id(),
                self.element.get_id(), "", guard_exp, event_name)
            assert len(locations) == 0 and len(edges) == 1, \
                f"Expected one edge for self-loops, got {len(edges)} edges."
            self.automaton.add_edge(edges[0])
            self._events_no_condition.append(event_name)

    def write_model(self):
        state_name = self.element.get_id()
        self.automaton.add_location(state_name)
        # Dictionary tracking the conditional trigger-based transitions
        self._event_to_conditions: Dict[str, List[str]] = {}
        # List of events that trigger transitions without conditions
        self._events_no_condition: List[str] = []
        for child in self.children:
            transition_events = child.element.get_events()
            transition_event = "" if len(transition_events) == 0 else transition_events[0]
            transition_condition = child.element.get_condition()
            # Add previous conditions matching the same event trigger to the current child state
            child.set_previous_siblings_conditions(
                self._event_to_conditions.get(transition_event, []))
            if transition_condition is None:
                # Make sure we do not have multiple transitions with no condition and same event
                assert transition_event not in self._events_no_condition, \
                    f"Event {transition_event} in state {self.element.get_id()} already has a" \
                    "transition without condition."
                self._events_no_condition.append(transition_event)
            else:
                # Update the list of conditions related to a transition trigger
                if transition_event not in self._event_to_conditions:
                    self._event_to_conditions[transition_event] = []
                self._event_to_conditions[transition_event].append(transition_condition)
            child.write_model()


class TransitionTag(BaseTag):
    """Object representing a transition tag from a SCXML file.

    See https://www.w3.org/TR/scxml/#transition
    """

    def get_children(self) -> List[ScxmlBase]:
        return []

    def set_previous_siblings_conditions(self, conditions_scripts: List[str]):
        """Add conditions from previous transitions with same event trigger."""
        self._previous_conditions = conditions_scripts

    def write_model(self):
        assert hasattr(self, "_previous_conditions"), \
            "Make sure 'set_previous_siblings_conditions' was called before."
        scxml_root: ScxmlRoot = self.call_trace[0]
        current_state: ScxmlState = self.call_trace[-1]
        current_state_id: str = current_state.get_id()
        target_state_id: str = self.element.get_target_state_id()
        target_state: ScxmlState = scxml_root.get_state_by_id(target_state_id)
        assert target_state is not None, f"Transition's target state {target_state_id} not found."
        event_name = self.element.get_events()
        # TODO: Need to extend this to support multiple events
        assert len(event_name) == 0 or len(event_name) == 1, \
            "Transitions triggered by multiple events are not supported."
        transition_trigger_event = None if len(event_name) == 0 else event_name[0]
        if transition_trigger_event is not None:
            # TODO: Maybe get rid of one of the two event variables
            assert len(transition_trigger_event) > 0, "Empty event name not supported."
            action_name = transition_trigger_event + "_on_receive"
            if not self.events_holder.has_event(transition_trigger_event):
                new_event = Event(
                    transition_trigger_event
                    # we can't know the data structure here
                )
                self.events_holder.add_event(new_event)
            existing_event = self.events_holder.get_event(transition_trigger_event)
            existing_event.add_receiver(self.automaton.get_name(), action_name)
        # Prepare the previous expressions for the transition guard
        previous_expressions = [
            parse_ecmascript_to_jani_expression(cond) for cond in self._previous_conditions]
        if event_name is not None:
            for expr in previous_expressions:
                expr.replace_event(transition_trigger_event)
        transition_condition = self.element.get_condition()
        if transition_condition is not None:
            current_expression = parse_ecmascript_to_jani_expression(transition_condition)
            if event_name is not None:
                current_expression.replace_event(transition_trigger_event)
            # If there are multiple transitions for an event, consider the previous conditions
            merged_expression = _merge_conditions(previous_expressions, current_expression)
            guard = merged_expression
        else:
            if len(previous_expressions) > 0:
                guard = _merge_conditions(previous_expressions)
            else:
                guard = None

        original_transition_body = self.element.get_executable_body()

        merged_transition_body = []
        if current_state.get_onexit() is not None:
            merged_transition_body.extend(current_state.get_onexit())
        merged_transition_body.extend(original_transition_body)
        if target_state.get_onentry() is not None:
            merged_transition_body.extend(target_state.get_onentry())
        # We assume that each transition has a unique combination of the entries below
        # TODO: If so, we could come up with a more descriptive name, instead of hashing?
        hash_str = _hash_element([
            current_state_id, target_state_id, event_name, transition_condition])
        new_edges, new_locations = _append_scxml_body_to_jani_automaton(
            self.automaton, self.events_holder, merged_transition_body, current_state_id,
            target_state_id, hash_str, guard, transition_trigger_event)
        for edge in new_edges:
            self.automaton.add_edge(edge)
        for loc in new_locations:
            self.automaton.add_location(loc)


CLASS_BY_TYPE = {
    ScxmlDataModel: DatamodelTag,
    ScxmlRoot: ScxmlTag,
    ScxmlState: StateTag,
    ScxmlTransition: TransitionTag,
}
