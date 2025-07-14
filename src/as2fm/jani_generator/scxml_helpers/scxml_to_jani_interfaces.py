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
Interface classes between SCXML tags and related JANI output.
"""

from typing import Any, Dict, List, MutableSequence, Optional, Set, Tuple

from as2fm.as2fm_common.common import EPSILON, get_array_type_and_sizes, get_padded_array
from as2fm.as2fm_common.ecmascript_interpretation import (  # get_esprima_expr_type,
    get_array_expr_as_list,
    interpret_ecma_script_expr,
)
from as2fm.as2fm_common.logging import check_assertion
from as2fm.jani_generator.jani_entries import (
    JaniAutomaton,
    JaniEdge,
    JaniExpression,
    JaniValue,
    JaniVariable,
)
from as2fm.jani_generator.jani_entries.jani_expression_generator import array_value_operator
from as2fm.jani_generator.scxml_helpers.scxml_event import Event, EventsHolder, is_event_synched
from as2fm.jani_generator.scxml_helpers.scxml_expression import (
    get_array_length_var_name,
    parse_ecmascript_to_jani_expression,
)
from as2fm.jani_generator.scxml_helpers.scxml_to_jani_interfaces_helpers import (
    append_scxml_body_to_jani_automaton,
    append_scxml_body_to_jani_edge,
    hash_element,
    merge_conditions,
)
from as2fm.scxml_converter.bt_converter import is_bt_root_scxml
from as2fm.scxml_converter.data_types.type_utils import (
    ArrayInfo,
    check_variable_base_type_ok,
    get_array_info,
    get_data_type_from_string,
    is_type_string_array,
    is_type_string_base_type,
)
from as2fm.scxml_converter.scxml_entries import (
    ScxmlBase,
    ScxmlDataModel,
    ScxmlRoot,
    ScxmlState,
    ScxmlTransition,
    ScxmlTransitionTarget,
)

# The supported MutableSequence instances
SupportedMutableSequence = (MutableSequence[int], MutableSequence[float])
# The resulting types from the SCXML conversion to Jani
ModelTupleType = Tuple[JaniAutomaton, EventsHolder]


class BaseTag:
    """Base class for all SCXML tags to interface."""

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

    def generate_tag_element(self, child: ScxmlBase) -> "BaseTag":
        """
        Simplified version of the "from_element" call.
        """
        return self.from_element(
            child,
            self.call_trace + [self.element],
            (self.automaton, self.events_holder),
            self.max_array_size,
        )

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
        self.model_variables: Optional[Dict[str, Any]] = None
        self.max_array_size = max_array_size
        self.element = element
        self.automaton, self.events_holder = model
        self.call_trace = call_trace
        scxml_children = self.get_children()
        self.children = [self.generate_tag_element(child) for child in scxml_children]

    def set_model_variables(self, mod_vars: Optional[Dict[str, Any]]):
        """
        Instantiate the internal variables defined in the SCXML model.

        :param mod_vars: A mapping from the variable name to its default value.
        """
        assert mod_vars is None or isinstance(mod_vars, Dict), f"Unexpected input {mod_vars}"
        self.model_variables = mod_vars
        for child in self.children:
            child.set_model_variables(mod_vars)

    def get_children(
        self,
    ) -> List[ScxmlBase]:
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
        assert self.model_variables is None, "Expected model_variables to be unset at this stage."
        self.model_variables: Dict[str, Any] = {}
        assert isinstance(self.element, ScxmlDataModel)
        check_assertion(
            self.element.is_plain_scxml(),
            self.element.get_xml_origin(),
            "Invalid data_model element found.",
        )
        for scxml_data in self.element.get_data_entries():
            scxml_origin = scxml_data.get_xml_origin()
            data_type_str = scxml_data.get_type_str()
            array_info: Optional[ArrayInfo] = None
            data_type: type = None
            if is_type_string_array(data_type_str):
                array_info = get_array_info(data_type_str)
                array_info.substitute_unbounded_dims(self.max_array_size)
                data_type = MutableSequence
            else:
                check_assertion(
                    is_type_string_base_type(data_type_str),
                    scxml_data.get_xml_origin(),
                    f"Unexpected type {data_type_str} found in scxml data.",
                )
                data_type = get_data_type_from_string(data_type_str)
                # Special handling of strings: treat them as array of integers
                if data_type is str:
                    # Keep data_type == str, since we use it for the JS evaluation.
                    array_info = ArrayInfo(int, 1, [self.max_array_size])
            evaluated_expr = interpret_ecma_script_expr(scxml_data.get_expr(), self.model_variables)
            # TODO: This special casing is needed since JavaScript typing is funny
            if data_type is float and isinstance(evaluated_expr, int):
                evaluated_expr = float(evaluated_expr)
            check_assertion(
                check_variable_base_type_ok(evaluated_expr, data_type, array_info),
                scxml_data.get_xml_origin(),
                f"Expression >{scxml_data.get_expr()}< did not evaluate to the expected "
                + f"type {data_type} (according to type string {data_type_str}).",
            )
            data_type = get_data_type_from_string(data_type_str)
            if data_type is MutableSequence:
                # Extract ArrayInfo from data_type_str.
                data_type = get_array_info(data_type_str)
            elif data_type is str:
                # Special handling of strings: treat them as array of integers
                data_type = ArrayInfo(int, 1, [self.max_array_size])
            # Explicitly prevent the use of existing  variable in data expression
            # evaluated_expr_type = get_esprima_expr_type(scxml_data.get_expr(), {}, scxml_origin)
            # check_assertion(
            #     evaluated_expr_type == data_type,
            #     scxml_origin,
            #     f"Invalid type of '{scxml_data.get_name()}': expected type "
            #     f"{data_type} != {evaluated_expr_type}",
            # )
            jani_data_init_expr = parse_ecmascript_to_jani_expression(
                scxml_data.get_expr(), scxml_origin, array_info
            )
            # JANI has no knowledge of strings, consider it an array of integers
            jani_type = MutableSequence if isinstance(data_type, ArrayInfo) else data_type
            # TODO: Add support for lower and upper bounds
            self.automaton.add_variable(
                JaniVariable(
                    scxml_data.get_name(), jani_type, jani_data_init_expr, False, array_info
                )
            )
            # In case of arrays, declare a number of additional 'length' variables is required
            if array_info is not None:
                # Add the array-length values in the model
                # TODO: The length variable NEEDS to be bounded in jani, between 0 and max_length
                data_expr_as_list = get_array_expr_as_list(scxml_data.get_expr(), scxml_origin)
                _, array_sizes = get_array_type_and_sizes(data_expr_as_list)
                for level in range(array_info.array_dimensions):
                    var_len_name = get_array_length_var_name(scxml_data.get_name(), level + 1)
                    if level == 0:
                        self.automaton.add_variable(
                            JaniVariable(var_len_name, int, JaniValue(array_sizes[level]))
                        )
                    else:
                        # Handle the case in which the default value is empty at a specific level
                        if len(array_sizes) <= level:
                            assert len(array_sizes) == level
                            array_sizes.append([])
                        dim_array_info = ArrayInfo(int, level, array_info.array_max_sizes[0:level])
                        array_sizes[level] = get_padded_array(
                            array_sizes[level],
                            dim_array_info.array_max_sizes,
                            dim_array_info.array_type,
                        )
                        sizes_expr = array_value_operator(array_sizes[level])
                        self.automaton.add_variable(
                            JaniVariable(
                                var_len_name, MutableSequence, sizes_expr, False, dim_array_info
                            )
                        )
            self.model_variables.update({scxml_data.get_name(): data_type})


class ScxmlTag(BaseTag):
    """Object representing the root SCXML tag."""

    def get_children(self) -> List[ScxmlState]:
        root_children = []
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
            hash_str = hash_element([source_state, target_state, "onentry"])
            new_edges, new_locations = append_scxml_body_to_jani_automaton(
                self.automaton,
                self.events_holder,
                self.model_variables,
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
        # Extract information from ScxmlDatamodel
        data_model = self.element.get_data_model()
        # A map from the variable name to its default value
        if data_model is not None:
            data_element: DatamodelTag = self.generate_tag_element(data_model)
            data_element.write_model()
            self.model_variables = data_element.model_variables
        for state_entry in self.children:
            state_entry.set_model_variables(self.model_variables)
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
            parse_ecmascript_to_jani_expression(cond, None)
            for cond in self._event_to_conditions.get(event_name, [])
        ]
        if len(previous_expressions) > 0:
            return merge_conditions(previous_expressions)
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
            edges, locations = append_scxml_body_to_jani_automaton(
                self.automaton,
                self.events_holder,
                self.model_variables,
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
                f"Model {self.call_trace[0].get_name()} has an event {transition_event} in state "
                f"{self.element.get_id()} that has already a base exit condition."
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
            eventless_hash = hash_element([current_state_id, current_condition])
            action_name = f"transition-{current_state_id}-eventless-{eventless_hash}"
        transition_targets: List[ScxmlTransitionTarget] = self.element.get_targets()
        # Transition condition (guard) processing
        previous_conditions_expr = [
            parse_ecmascript_to_jani_expression(cond, self.element.get_xml_origin())
            for cond in self._previous_conditions
        ]
        current_condition_expr = None
        if current_condition is not None:
            current_condition_expr = parse_ecmascript_to_jani_expression(
                current_condition, self.element.get_xml_origin()
            )
        if trigger_event is not None:
            for single_cond_expr in previous_conditions_expr:
                single_cond_expr.replace_event(trigger_event)
            if current_condition_expr is not None:
                current_condition_expr.replace_event(trigger_event)
        jani_guard = merge_conditions(previous_conditions_expr, current_condition_expr)
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
            target_hash = hash_element(
                [
                    current_state_id,
                    target_state_id,
                    action_name,
                    current_condition,
                    str(total_probability),
                ]
            )
            additional_edges, additional_locations = append_scxml_body_to_jani_edge(
                transition_edge,
                self.automaton,
                self.events_holder,
                self.model_variables,
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
