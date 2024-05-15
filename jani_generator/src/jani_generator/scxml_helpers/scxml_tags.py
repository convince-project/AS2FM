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
Module defining ScXML tags to match against.
"""

import xml.etree.ElementTree as ET
from hashlib import sha256
from typing import Any, Dict, List, Optional, Tuple, Union

from mc_toolchain_jani_common.common import remove_namespace
from mc_toolchain_jani_common.ecmascript_interpretation import interpret_ecma_script_expr
from jani_generator.jani_entries import JaniModel
from jani_generator.jani_entries.jani_assignment import JaniAssignment
from jani_generator.jani_entries.jani_automaton import JaniAutomaton
from jani_generator.jani_entries.jani_composition import JaniComposition
from jani_generator.jani_entries.jani_edge import JaniEdge
from jani_generator.jani_entries.jani_expression import JaniExpression
from jani_generator.jani_entries.jani_guard import JaniGuard
from jani_generator.jani_entries.jani_variable import JaniVariable
from jani_generator.scxml_helpers.scxml_data import ScxmlData
from jani_generator.scxml_helpers.scxml_event import Event, EventsHolder
from jani_generator.scxml_helpers.scxml_expression import \
    parse_ecmascript_to_jani_expression

# The type to be exctended by parsing the scxml file
ModelTupleType = Tuple[JaniAutomaton, EventsHolder]


def _hash_element(element: ET.Element) -> str:
    """
    Hash an ElementTree element.
    :param element: The element to hash.
    :return: The hash of the element.
    """
    s = ET.tostring(element, encoding='unicode', method='xml')
    return sha256(s.encode()).hexdigest()[:32]


def _get_state_name(element: ET.Element) -> str:
    """Get the name of a state element."""
    assert remove_namespace(element.tag) == 'state', \
        f"Expected state, got {element.tag}"
    if 'id' in element.attrib:
        return element.attrib['id']
    else:
        raise NotImplementedError('Only states with an id are supported.')


def _interpret_scxml_executable_content(element: ET.Element) -> Union[
    JaniAssignment,
    JaniExpression
]:
    """Interpret the executable content of an SCXML element.

    :param element: The SCXML element to interpret.
    :return: The action or expression to be executed.
    """
    if remove_namespace(element.tag) == 'assign':
        return JaniAssignment({
            "ref": element.attrib['location'],
            "value": parse_ecmascript_to_jani_expression(element.attrib['expr'])
        })
    else:
        raise NotImplementedError(
            f'Element {remove_namespace(element.tag)} not implemented')


class BaseTag:
    """Base class for all ScXML tags."""
    # class function to initialize the correct tag object
    @staticmethod
    def from_element(element: ET.Element,
                     call_trace: List[ET.Element],
                     model: ModelTupleType) -> 'ScxmlTag':
        """Return the correct tag object based on the xml element.

        :param element: The xml element representing the tag.
        :return: The corresponding tag object.
        """
        tag = remove_namespace(element.tag)
        if tag not in CLASS_BY_TAG:
            raise NotImplementedError(f"Tag {tag} not implemented.")
        return CLASS_BY_TAG[tag](element, call_trace, model)

    def __init__(self, element: ET.Element,
                 call_trace: List[ET.Element],
                 model: ModelTupleType) -> None:
        """Initialize the ScxmlTag object from an xml element.

        :param element: The xml element representing the tag.
        """
        self.element = element
        self.call_trace = call_trace
        self.model = model
        self.automaton, self.events_holder = model
        self.children = [
            BaseTag.from_element(child, call_trace + [element], model)
            for child in element]

    def get_tag_name(self) -> str:
        """Return the tag name to match against.

        :return: For example, 'datamodel' for a DatamodelTag.
        """
        if type(self).__name__ == 'ScxmlTag':
            raise NotImplementedError(
                "This method must be implemented in a subclass.")
        return type(self).__name__.replace("Tag", "").lower()

    def write_model(self):
        """Return the model of the tag.

        :return: The model of the tag.
        """
        for child in self.children:
            child.write_model()


class Assign(BaseTag):
    """Object representing an assign tag from a ScXML file.

    See https://www.w3.org/TR/scxml/#assign
    """


class DatamodelTag(BaseTag):
    """Object representing a datamodel tag from a ScXML file.

    See https://www.w3.org/TR/scxml/#datamodel
    """


class DataTag(BaseTag):
    """Object representing a data tag from a ScXML file.

    See https://www.w3.org/TR/scxml/#data
    """

    def write_model(self):
        sd = ScxmlData(self.element)
        self.automaton.add_variable(sd.to_jani_variable())
        if len(self.children) > 0:
            raise NotImplementedError(
                "Children of the data tag are currently not supported.")


class LogTag(BaseTag):
    """Object representing a log tag from a ScXML file.

    Currently, this tag is not ignored.
    """


class OnEntryTag(BaseTag):
    """Object representing an onentry tag from a ScXML file.

    No implementation needed, because the children are already processed.
    """


class ParamTag(BaseTag):
    """Object representing a param tag from a ScXML file.

    No implementation needed, because the children are already processed.
    """


class ScxmlTag(BaseTag):
    """Object representing a generic ScXML tag."""

    def write_model(self):
        if 'name' in self.element.attrib:
            p_name = self.element.attrib['name']
        else:
            p_name = _hash_element(self.element)
        self.automaton.set_name(p_name)
        super().write_model()
        if 'initial' in self.element.attrib:
            self.automaton.make_initial(self.element.attrib['initial'])


class SendTag(BaseTag):
    """Object representing a send tag from a ScXML file.

    See https://www.w3.org/TR/scxml/#send
    """

    def write_model(self):
        event_name = self.element.attrib["event"]
        params = {}
        for child in self.element:
            if remove_namespace(child.tag) == 'param':
                expr = child.attrib['expr']
                variables = {}
                for n, v in self.automaton.get_variables().items():
                    variables[n] = v.get_type()()
                obj = interpret_ecma_script_expr(expr, variables)
                p_type = type(obj)
                p_name = child.attrib['name']
                params[p_name] = {}
                params[p_name]['type'] = p_type
                params[p_name]['jani_expr'] = parse_ecmascript_to_jani_expression(
                    expr)
        assignments = []
        for p_name, param in params.items():
            assignments.append(JaniAssignment({
                "ref": f'{event_name}.{p_name}',
                "value": param['jani_expr'],
                "index": 0
            }))
        # Additional flag to signal the value from the event is now valid
        assignments.append(JaniAssignment({
            "ref": f'{event_name}.valid',
            "value": True,
            "index": 1
        }))
        data_struct = {name: params[name]['type'] for name in params}
        if not self.events_holder.has_event(event_name):
            new_event = Event(
                event_name,
                data_struct=data_struct
            )
            self.events_holder.add_event(new_event)
        existing_event = self.events_holder.get_event(event_name)
        existing_event.data_struct = data_struct
        if remove_namespace(self.call_trace[-1].tag) == 'onentry':
            entity_name = _get_state_name(self.call_trace[-2])
            existing_event.add_sender_on_entry(
                self.automaton.get_name(), entity_name, assignments)
        elif remove_namespace(self.call_trace[-1].tag) == 'onexit':
            entity_name = _get_state_name(self.call_trace[-2])
            existing_event.add_sender_on_exit(
                self.automaton.get_name(), entity_name, assignments)
        elif remove_namespace(self.call_trace[-1].tag) == 'transition':
            transition = self.call_trace[-1]
            assert 'transition' in transition.tag, \
                f"Expected transition, got {transition.tag}"
            action_name = transition.attrib['event'] + "_on_send"
            existing_event.add_sender_edge(
                self.automaton.get_name(), action_name, assignments)
        else:
            raise RuntimeError(
                'Unknown place for send element: ' +
                f'{remove_namespace(self.call_trace[-1].tag)}')


class TransitionTag(BaseTag):
    """Object representing a transition tag from a ScXML file.

    See https://www.w3.org/TR/scxml/#transition
    """

    def write_model(self):
        parent_name = _get_state_name(self.call_trace[-1])
        action_name = None
        if 'event' in self.element.attrib:
            event_name = self.element.attrib['event']
            action_name = event_name + "_on_receive"
            if not self.events_holder.has_event(event_name):
                new_event = Event(
                    event_name
                    # we can't know the data structure here
                )
                self.events_holder.add_event(new_event)
            existing_event = self.events_holder.get_event(event_name)
            existing_event.add_receiver(
                self.automaton.get_name(), parent_name, action_name)
        if 'target' in self.element.attrib:
            target = self.element.attrib['target']
        else:
            target = None
        if 'cond' in self.element.attrib:
            expression = parse_ecmascript_to_jani_expression(
                    self.element.attrib['cond'])
            if 'event' in self.element.attrib:
                expression.replace_event(event_name)
            guard = JaniGuard(
                expression
            )
        else:
            guard = None
        assignments = []
        for child in self.element:
            if remove_namespace(child.tag) != 'send':
                child = _interpret_scxml_executable_content(child)
                if isinstance(child, JaniAssignment):
                    if 'event' in self.element.attrib:
                        child._value.replace_event(event_name)
                    assignments.append(child)
                else:
                    raise NotImplementedError(
                        f'Element {remove_namespace(child.tag)} not implemented')
            else: # send tag
                assert action_name is None, \
                    "Transistions can only either send or receive events, not both."
                action_name = child.attrib['event'] + "_on_send"
            self.automaton.add_edge(JaniEdge({
                "location": parent_name,
                "action": action_name,
                "guard": guard,
                "destinations": [{
                    "location": target,
                    "assignments": assignments
                }]
            }))
        super().write_model()


class StateTag(BaseTag):
    """Object representing a state tag from a ScXML file.

    See https://www.w3.org/TR/scxml/#state
    """

    def write_model(self):
        p_name = _get_state_name(self.element)
        self.automaton.add_location(p_name)
        super().write_model()


CLASS_BY_TAG = {
    'assign': Assign,
    'data': DataTag,
    'datamodel': DatamodelTag,
    'log': LogTag,
    'onentry': OnEntryTag,
    'param': ParamTag,
    'scxml': ScxmlTag,
    'send': SendTag,
    'state': StateTag,
    'transition': TransitionTag,
}
