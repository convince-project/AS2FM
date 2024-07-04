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
from typing import List, Optional, Tuple, Union

from jani_generator.jani_entries import (JaniAssignment, JaniAutomaton,
                                         JaniEdge, JaniExpression, JaniGuard,
                                         JaniVariable)
from jani_generator.jani_entries.jani_expression_generator import (
    and_operator, not_operator)

from jani_generator.scxml_helpers.scxml_data import ScxmlData
from jani_generator.scxml_helpers.scxml_event import Event, EventsHolder
from jani_generator.scxml_helpers.scxml_expression import \
    parse_ecmascript_to_jani_expression
from mc_toolchain_jani_common.common import remove_namespace
from mc_toolchain_jani_common.ecmascript_interpretation import \
    interpret_ecma_script_expr
from scxml_converter.scxml_entries import (ScxmlAssign, ScxmlBase,
                                           ScxmlDataModel, ScxmlExecutionBody,
                                           ScxmlIf, ScxmlRoot, ScxmlSend,
                                           ScxmlState)

# The type to be exctended by parsing the scxml file
ModelTupleType = Tuple[JaniAutomaton, EventsHolder]


def _hash_element(element: Union[ET.Element, ScxmlBase]) -> str:
    """
    Hash an ElementTree element.
    :param element: The element to hash.
    :return: The hash of the element.
    """
    if isinstance(element, ET.Element):
        s = ET.tostring(element, encoding='unicode', method='xml')
    elif isinstance(element, ScxmlBase):
        s = ET.tostring(element.as_xml(), encoding='unicode', method='xml')
    else:
        raise ValueError(f"Element type {type(element)} not supported.")
    return sha256(s.encode()).hexdigest()[:8]


def _get_state_name(element: ET.Element) -> str:
    """Get the name of a state element."""
    assert remove_namespace(element.tag) == 'state', \
        f"Expected state, got {element.tag}"
    if 'id' in element.attrib:
        return element.attrib['id']
    else:
        raise NotImplementedError('Only states with an id are supported.')


def _interpret_scxml_assign(
        elem: ScxmlAssign, event_substitution: Optional[str] = None) -> JaniAssignment:
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
        "value": assignment_value
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


class AssignTag(BaseTag):
    """Object representing an assign tag from a SCXML file.

    See https://www.w3.org/TR/scxml/#assign
    """


class DatamodelTag(BaseTag):
    """Object representing a datamodel tag from a SCXML file.

    See https://www.w3.org/TR/scxml/#datamodel
    """

    def get_children(self) -> List[ScxmlBase]:
        return []

    def write_model(self):
        for name, expr in self.element.get_data_entries():
            assert expr is not None, f"No init value for {name}."
            # TODO: ScxmlData from scxml_helpers provide many more options.
            # It should be ported to scxml_entries.ScxmlDataModel
            init_value = interpret_ecma_script_expr(expr)
            expr_type = type(init_value)
            self.automaton.add_variable(
                JaniVariable(name, expr_type, init_value))


class ElseTag(BaseTag):
    """Object representing an else tag from a SCXML file.

    No implementation needed, because the children are already processed.
    """


class ElseIfTag(BaseTag):
    """Object representing an elseif tag from a SCXML file.

    No implementation needed, because the children are already processed.
    """


class IfTag(BaseTag):
    """Object representing an if tag from a SCXML file.

    No implementation needed, because the children are already processed.
    """


class OnEntryTag(BaseTag):
    """Object representing an onentry tag from a SCXML file.

    No implementation needed, because the children are already processed.
    """


class OnExitTag(BaseTag):
    """Object representing an onexid tag from a SCXML file.

    No implementation needed, because the children are already processed.
    """


class ParamTag(BaseTag):
    """Object representing a param tag from a SCXML file.

    No implementation needed, because the children are already processed.
    """


class ScxmlTag(BaseTag):
    """Object representing the root SCXML tag."""

    def get_children(self) -> List[ScxmlBase]:
        root_children = []
        data_model = self.element.get_data_model()
        if data_model is not None:
            root_children.append(data_model)
        root_children.extend(self.element.get_states())
        return []

    def write_model(self):
        assert isinstance(self.element, ScxmlRoot), \
            f"Expected ScxmlRoot, got {type(self.element)}."
        self.automaton.set_name(self.element.get_name())
        super().write_model()
        # Note: we don't support the initial tag (as state) https://www.w3.org/TR/scxml/#initial
        self.automaton.make_initial(self.element.get_initial_state_id())


class SendTag(BaseTag):
    """Object representing a send tag from a SCXML file.

    See https://www.w3.org/TR/scxml/#send
    """


class TransitionTag(BaseTag):
    """Object representing a transition tag from a SCXML file.

    See https://www.w3.org/TR/scxml/#transition
    """

    def interpret_scxml_executable_content_body(
            self,
            body: ScxmlExecutionBody,
            source: str,
            target: str,
            hash_str: str,
            guard: Optional[JaniGuard] = None,
            trigger_event_action: Optional[str] = None
    ) -> List[JaniEdge]:
        """Interpret a body of executable content of an SCXML element.

        :param body: The body of the SCXML element to interpret.
        :return: The edges that contain the actions and expressions to be executed.
        """
        edge_action_name = f"{source}-{target}-{hash_str}"
        new_edges = []
        new_locations = []
        # First edge. Has to evaluate guard and trigger event of original transition.
        new_edges.append(JaniEdge({
            "location": source,
            "action": (trigger_event_action
                       if trigger_event_action is not None else edge_action_name),
            "guard": guard.expression if guard is not None else None,
            "destinations": [{
                "location": None,
                "assignments": []
            }]
        }))
        for i, ec in enumerate(body):
            if isinstance(ec, ScxmlAssign):
                jani_assignment = _interpret_scxml_assign(ec, self._trans_event_name)
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
                    expr = param.get_expr() if param.get_expr() is not None else param.get_location()
                    new_edge.destinations[0]['assignments'].append(JaniAssignment({
                        "ref": f'{ec.get_event()}.{param.get_name()}',
                        "value": parse_ecmascript_to_jani_expression(
                            expr).replace_event(self._trans_event_name)
                    }))
                    variables = {}
                    for n, v in self.automaton.get_variables().items():
                        variables[n] = v.get_type()()
                    data_structure_for_event[param.get_name()] = \
                        type(interpret_ecma_script_expr(expr, variables))
                new_edge.destinations[0]['assignments'].append(JaniAssignment({
                    "ref": f'{ec.get_event()}.valid',
                    "value": True
                }))

                if not self.events_holder.has_event(event_name):
                    send_event = Event(
                        event_name,
                        data_structure_for_event
                    )
                    self.events_holder.add_event(send_event)
                else:
                    send_event = self.events_holder.get_event(event_name)
                    send_event.set_data_structure(
                        data_structure_for_event
                    )
                send_event.add_sender_edge(
                    self.automaton.get_name(), event_send_action_name, [])

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
                        previous_conditions, current_cond).replace_event(self._trans_event_name)
                    sub_edges, sub_locs = self.interpret_scxml_executable_content_body(
                        conditional_body, interm_loc_before, interm_loc_after,
                        '-'.join([hash_str, _hash_element(ec), cond_str]),
                        JaniGuard(jani_cond), None)
                    new_edges.extend(sub_edges)
                    new_locations.extend(sub_locs)
                    previous_conditions.append(current_cond)
                # Add else branch:
                if ec.get_else_execution() is not None:
                    print(f"Else: {ec.get_else_execution()}")
                    jani_cond = _merge_conditions(
                        previous_conditions).replace_event(self._trans_event_name)
                    sub_edges, sub_locs = self.interpret_scxml_executable_content_body(
                        ec.get_else_execution(), interm_loc_before, interm_loc_after,
                        '-'.join([hash_str, _hash_element(ec), 'else']),
                        JaniGuard(jani_cond), None)
                    new_edges.extend(sub_edges)
                    new_locations.extend(sub_locs)
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

    def write_model(self):
        parent_name = _get_state_name(self.call_trace[-1])
        action_name = None
        self._trans_event_name = None
        if 'event' in self.element.attrib:
            self._trans_event_name = self.element.attrib['event']
            assert len(self._trans_event_name) > 0, "Empty event name not supported."
            assert " " not in self._trans_event_name, "Multiple events not supported."
            action_name = self._trans_event_name + "_on_receive"
            if not self.events_holder.has_event(self._trans_event_name):
                new_event = Event(
                    self._trans_event_name
                    # we can't know the data structure here
                )
                self.events_holder.add_event(new_event)
            existing_event = self.events_holder.get_event(self._trans_event_name)
            existing_event.add_receiver(
                self.automaton.get_name(), parent_name, action_name)
        if 'target' in self.element.attrib:
            target = self.element.attrib['target']
        else:
            raise RuntimeError('Target attribute is mandatory.')
        if 'cond' in self.element.attrib:
            expression = parse_ecmascript_to_jani_expression(
                self.element.attrib['cond'])
            if 'event' in self.element.attrib:
                expression.replace_event(self._trans_event_name)
            guard = JaniGuard(
                expression
            )
        else:
            guard = None
        original_transition_body = []

        root = self.call_trace[0]
        for child in root.iter():
            child.tag = remove_namespace(child.tag)

        for child in self.element:
            if remove_namespace(child.tag) == 'send':
                original_transition_body.append(ScxmlSend.from_xml_tree(child))
            elif remove_namespace(child.tag) == 'if':
                original_transition_body.append(ScxmlIf.from_xml_tree(child))
            elif remove_namespace(child.tag) == 'assign':
                original_transition_body.append(ScxmlAssign.from_xml_tree(child))
            else:
                raise ValueError(
                    f"Tag {remove_namespace(child.tag)} not supported.")

        # TODO, the children should also contain onexit of the source state
        # and onentry of the target state
        root_scxml = ScxmlRoot.from_xml_tree(root)
        source_state = root_scxml.get_state_by_id(parent_name)
        assert source_state is not None, f"Source state {parent_name} not found."
        target_state = root_scxml.get_state_by_id(target)
        assert target_state is not None, f"Target state {target} not found."

        transition_body = []
        if source_state.get_onexit() is not None:
            transition_body.extend(source_state.get_onexit())
        transition_body.extend(original_transition_body)
        if target_state.get_onentry() is not None:
            transition_body.extend(target_state.get_onentry())

        hash_str = _hash_element(self.element)
        new_edges, new_locations = self.interpret_scxml_executable_content_body(
            transition_body, parent_name, target, hash_str, guard, action_name)
        for edge in new_edges:
            self.automaton.add_edge(edge)
        for loc in new_locations:
            self.automaton.add_location(loc)


class StateTag(BaseTag):
    """Object representing a state tag from a SCXML file.

    See https://www.w3.org/TR/scxml/#state
    """

    def write_model(self):
        p_name = _get_state_name(self.element)
        self.automaton.add_location(p_name)
        # TODO: Make sure initial states that have onentry execute the onentry block at start
        super().write_model()


CLASS_BY_TYPE = {
    ScxmlDataModel: DatamodelTag,
    ScxmlRoot: ScxmlTag,
    # ScxmlState: StateTag TODO
}

CLASS_BY_TAG = {
    'assign': AssignTag,
    'data': DataTag,
    'datamodel': DatamodelTag,
    'else': ElseTag,
    'elseif': ElseIfTag,
    'if': IfTag,
    'onexit': OnExitTag,
    'onentry': OnEntryTag,
    'param': ParamTag,
    'scxml': ScxmlTag,
    'send': SendTag,
    'state': StateTag,
    'transition': TransitionTag,
}
