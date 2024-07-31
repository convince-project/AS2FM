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
from typing import Dict, List, Optional, Set, Tuple, Union

from jani_generator.jani_entries import (JaniAssignment, JaniAutomaton,
                                         JaniEdge, JaniExpression, JaniGuard,
                                         JaniVariable)
from jani_generator.jani_entries.jani_expression_generator import (
    and_operator, not_operator)

from jani_generator.scxml_helpers.scxml_event import Event, EventsHolder
from jani_generator.scxml_helpers.scxml_expression import \
    parse_ecmascript_to_jani_expression
from as2fm_common.ecmascript_interpretation import \
    interpret_ecma_script_expr
from scxml_converter.scxml_entries import (ScxmlAssign, ScxmlBase, ScxmlData,
                                           ScxmlDataModel, ScxmlExecutionBody,
                                           ScxmlIf, ScxmlRoot, ScxmlSend,
                                           ScxmlState, ScxmlTransition)

# The type to be exctended by parsing the scxml file
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


def _interpret_scxml_assign(elem: ScxmlAssign, event_substitution: Optional[str] = None,
                            assign_index: int = 0) -> JaniAssignment:
    """Interpret SCXML assign element.

    :param element: The SCXML element to interpret.
    :return: The action or expression to be executed.
    """
    assert isinstance(elem, ScxmlAssign), \
        f"Expected ScxmlAssign, got {type(elem)}"
    assignment_value = parse_ecmascript_to_jani_expression(
        elem.get_expr())
    if isinstance(assignment_value, JaniExpression):
        assignment_value.replace_event(event_substitution)
    return JaniAssignment({
        "ref": elem.get_location(),
        "value": assignment_value,
        "index": assign_index
    })


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
                                         hash_str: str, guard: Optional[JaniGuard],
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
    # First edge. Has to evaluate guard and trigger event of original transition.
    new_edges.append(JaniEdge({
        "location": source,
        "action": trigger_event_action,
        "guard": guard.expression if guard is not None else None,
        "destinations": [{
            "location": None,
            "assignments": []
        }]
    }))
    for i, ec in enumerate(body):
        if isinstance(ec, ScxmlAssign):
            assign_index = len(new_edges[-1].destinations[0]['assignments'])
            jani_assignment = _interpret_scxml_assign(ec, trigger_event, assign_index)
            new_edges[-1].destinations[0]['assignments'].append(jani_assignment)
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
            data_structure_for_event = {}
            for param in ec.get_params():
                expr = param.get_expr() if param.get_expr() is not None else \
                    param.get_location()
                new_edge.destinations[0]['assignments'].append(JaniAssignment({
                    "ref": f'{ec.get_event()}.{param.get_name()}',
                    "value": parse_ecmascript_to_jani_expression(
                        expr).replace_event(trigger_event)
                }))
                variables = {}
                for n, v in jani_automaton.get_variables().items():
                    variables[n] = v.get_type()()
                data_structure_for_event[param.get_name()] = \
                    type(interpret_ecma_script_expr(expr, variables))
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
            interm_loc_before = f"{source}_{i}_before_if"
            interm_loc_after = f"{source}_{i}_after_if"
            new_edges[-1].destinations[0]['location'] = interm_loc_before
            previous_conditions = []
            for cond_str, conditional_body in ec.get_conditional_executions():
                print(f"Condition: {cond_str}")
                print(f"Body: {conditional_body}")
                current_cond = parse_ecmascript_to_jani_expression(cond_str)
                jani_cond = _merge_conditions(
                    previous_conditions, current_cond).replace_event(trigger_event)
                sub_edges, sub_locs = _append_scxml_body_to_jani_automaton(
                    jani_automaton, events_holder, conditional_body, interm_loc_before,
                    interm_loc_after, '-'.join([hash_str, _hash_element(ec), cond_str]),
                    JaniGuard(jani_cond), None)
                new_edges.extend(sub_edges)
                new_locations.extend(sub_locs)
                previous_conditions.append(current_cond)
            # Add else branch: if no else is provided, we assume an empty else body!
            else_execution_body = ec.get_else_execution()
            else_execution_body = [] if else_execution_body is None else else_execution_body
            print(f"Else: {ec.get_else_execution()}")
            jani_cond = _merge_conditions(
                previous_conditions).replace_event(trigger_event)
            sub_edges, sub_locs = _append_scxml_body_to_jani_automaton(
                jani_automaton, events_holder, ec.get_else_execution(), interm_loc_before,
                interm_loc_after, '-'.join([hash_str, _hash_element(ec), 'else']),
                JaniGuard(jani_cond), None)
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
                     model: ModelTupleType) -> 'BaseTag':
        """Return the correct tag object based on the xml element.

        :param element: The xml element representing the tag.
        :return: The corresponding tag object.
        """
        if type(element) not in CLASS_BY_TYPE:
            raise NotImplementedError(f"Support for SCXML type >{type(element)}< not implemented.")
        return CLASS_BY_TYPE[type(element)](element, call_trace, model)

    def __init__(self, element: ScxmlBase,
                 call_trace: List[ScxmlBase],
                 model: ModelTupleType) -> None:
        """Initialize the ScxmlTag object from an xml element.

        :param element: The xml element representing the tag.
        """
        self.element = element
        self.model = model
        self.automaton, self.events_holder = model
        self.call_trace = call_trace
        scxml_children = self.get_children()
        self.children = [
            BaseTag.from_element(child, call_trace + [element], model)
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
            init_value = parse_ecmascript_to_jani_expression(scxml_data.get_expr())
            expr_type = type(interpret_ecma_script_expr(scxml_data.get_expr()))
            assert expr_type == scxml_data.get_type(), \
                f"Expected type {scxml_data.get_type()}, got {expr_type}."
            # TODO: Add support for lower and upper bounds
            self.automaton.add_variable(
                JaniVariable(scxml_data.get_name(), scxml_data.get_type(), init_value))


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
        if initial_state.get_onentry() is not None:
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

    def get_guard_for_prev_conditions(self, event_name: str) -> Optional[JaniGuard]:
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
            guard = JaniGuard(_merge_conditions(previous_expressions))
        else:
            guard = None
        return guard

    def add_unhandled_transitions(self, transitions_set: Set[str]):
        """Add self-loops for transitions that weren't handled yet."""
        for event_name in transitions_set:
            if event_name in self._events_no_condition or len(event_name) == 0:
                continue
            guard = self.get_guard_for_prev_conditions(event_name)
            edges, locations = _append_scxml_body_to_jani_automaton(
                self.automaton, self.events_holder, [], self.element.get_id(),
                self.element.get_id(), "", guard, event_name)
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
            transition_event = "" if transition_events is None else transition_events[0]
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
        assert event_name is None or len(event_name) == 1, \
            "Transitions triggered by multiple events are not supported."
        transition_trigger_event = None if event_name is None else event_name[0]
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
            guard = JaniGuard(merged_expression)
        else:
            if len(previous_expressions) > 0:
                guard = JaniGuard(_merge_conditions(previous_expressions))
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
