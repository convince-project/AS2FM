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
A single state in SCXML. In XML, it has the tag `state`.
"""

from typing import List, Optional
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import (ScxmlExecutableEntry, ScxmlExecutionBody,
                                           ScxmlTransition, execution_body_from_xml,
                                           valid_execution_body)


class ScxmlState:
    """This class represents a single scxml state."""

    def __init__(self, id: str, *,
                 on_entry: Optional[ScxmlExecutionBody] = None,
                 on_exit: Optional[ScxmlExecutionBody] = None,
                 body: Optional[List[ScxmlTransition]] = None):
        self._id = id
        self._on_entry = on_entry
        self._on_exit = on_exit
        self._body = body

    def get_tag_name() -> str:
        return "state"

    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlState":
        """Create a ScxmlState object from an XML tree."""
        assert xml_tree.tag == ScxmlState.get_tag_name(), \
            f"Error: SCXML state: XML tag name is not {ScxmlState.get_tag_name()}."
        id = xml_tree.attrib.get("id")
        assert id is not None and len(id) > 0, "Error: SCXML state: id is not valid."
        scxml_state = ScxmlState(id)
        # Get the onentry and onexit execution bodies
        on_entry = xml_tree.findall("onentry")
        assert on_entry is None or len(on_entry) == 1, \
            "Error: SCXML state: multiple onentry tags found, up to 1 allowed."
        on_exit = xml_tree.findall("onexit")
        assert on_exit is None or len(on_exit) == 1, \
            "Error: SCXML state: multiple onexit tags found, up to 1 allowed."
        if on_entry is not None:
            for exec_entry in execution_body_from_xml(on_entry[0]):
                scxml_state.append_on_entry(exec_entry)
        if on_exit is not None:
            for exec_entry in execution_body_from_xml(on_exit[0]):
                scxml_state.append_on_exit(exec_entry)
        # Get the transitions in the state body
        transitions_xml = xml_tree.findall(ScxmlTransition.get_tag_name())
        if transitions_xml is not None:
            for transition_xml in transitions_xml:
                scxml_state.add_transition(ScxmlTransition.from_xml_tree(transition_xml))
        return scxml_state

    def get_id(self) -> str:
        return self._id

    def add_transition(self, transition: ScxmlTransition):
        if self._body is None:
            self._body = []
        self._body.append(transition)

    def append_on_entry(self, executable_entry: ScxmlExecutableEntry):
        if self._on_entry is None:
            self._on_entry = []
        self._on_entry.append(executable_entry)

    def append_on_exit(self, executable_entry: ScxmlExecutableEntry):
        if self._on_exit is None:
            self._on_exit = []
        self._on_exit.append(executable_entry)

    def check_validity(self) -> bool:
        valid_id = isinstance(self._id, str) and len(self._id) > 0
        valid_on_entry = self._on_entry is None or valid_execution_body(self._on_entry)
        valid_on_exit = self._on_exit is None or valid_execution_body(self._on_exit)
        valid_body = True
        if self._body is not None:
            valid_body = isinstance(self._body, list)
            if valid_body:
                for transition in self._body:
                    valid_transition = isinstance(
                        transition, ScxmlTransition) and transition.check_validity()
                    if not valid_transition:
                        valid_body = False
                        break
        if not valid_id:
            print("Error: SCXML state: id is not valid.")
        if not valid_on_entry:
            print("Error: SCXML state: on_entry is not valid.")
        if not valid_on_exit:
            print("Error: SCXML state: on_exit is not valid.")
        if not valid_body:
            print("Error: SCXML state: executable body is not valid.")
        return valid_on_entry and valid_on_exit and valid_body

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid state object."
        xml_state = ET.Element(ScxmlState.get_tag_name(), {"id": self._id})
        if self._on_entry is not None:
            xml_on_entry = ET.Element('onentry')
            for executable_entry in self._on_entry:
                xml_on_entry.append(executable_entry.as_xml())
            xml_state.append(xml_on_entry)
        if self._on_exit is not None:
            xml_on_exit = ET.Element('onexit')
            for executable_entry in self._on_exit:
                xml_on_exit.append(executable_entry.as_xml())
            xml_state.append(xml_on_exit)
        if self._body is not None:
            for transition in self._body:
                xml_state.append(transition.as_xml())
        return xml_state
