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

from typing import List, Optional, Union
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import (ScxmlBase, ScxmlExecutableEntry, ScxmlExecutionBody,
                                           ScxmlTransition, HelperRosDeclarations,
                                           execution_body_from_xml, valid_execution_body)


class ScxmlState(ScxmlBase):
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
        if on_entry is not None and len(on_entry) == 0:
            on_entry = None
        assert on_entry is None or len(on_entry) == 1, \
            f"Error: SCXML state: {len(on_entry)} onentry tags found, expected 0 or 1."
        on_exit = xml_tree.findall("onexit")
        if on_exit is not None and len(on_exit) == 0:
            on_exit = None
        assert on_exit is None or len(on_exit) == 1, \
            f"Error: SCXML state: {len(on_exit)} onexit tags found, expected 0 or 1."
        if on_entry is not None:
            for exec_entry in execution_body_from_xml(on_entry[0]):
                scxml_state.append_on_entry(exec_entry)
        if on_exit is not None:
            for exec_entry in execution_body_from_xml(on_exit[0]):
                scxml_state.append_on_exit(exec_entry)
        # Get the transitions in the state body
        for body_entry in ScxmlState._transitions_from_xml(xml_tree):
            scxml_state.add_transition(body_entry)
        return scxml_state

    def _transitions_from_xml(xml_tree: ET.Element) -> List[ScxmlTransition]:
        # import ros callbacks inheriting from ScxmlTransition
        from .scxml_ros_entries import RosRateCallback, RosTopicCallback
        transitions: List[ScxmlTransition] = []
        for child in xml_tree:
            if child.tag == ScxmlTransition.get_tag_name():
                transitions.append(ScxmlTransition.from_xml_tree(child))
            elif child.tag == RosRateCallback.get_tag_name():
                transitions.append(RosRateCallback.from_xml_tree(child))
            elif child.tag == RosTopicCallback.get_tag_name():
                transitions.append(RosTopicCallback.from_xml_tree(child))
        return transitions

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

    def check_valid_ros_instantiations(self, ros_declarations: HelperRosDeclarations) -> bool:
        """Check if the ros instantiations have been declared."""
        # Check onentry and onexit
        valid_entry = ScxmlState._check_valid_ros_instantiations(self._on_entry,
                                                                 ros_declarations)
        valid_exit = ScxmlState._check_valid_ros_instantiations(self._on_exit,
                                                                ros_declarations)
        valid_body = ScxmlState._check_valid_ros_instantiations(self._body,
                                                                ros_declarations)
        if not valid_entry:
            print("Error: SCXML state: onentry has invalid ROS instantiations.")
        if not valid_exit:
            print("Error: SCXML state: onexit has invalid ROS instantiations.")
        if not valid_body:
            print("Error: SCXML state: found invalid transition in state body.")
        return valid_entry and valid_exit and valid_body

    def _check_valid_ros_instantiations(body: List[Union[ScxmlExecutableEntry, ScxmlTransition]],
                                        ros_declarations: HelperRosDeclarations) -> bool:
        """Check if the ros instantiations have been declared in the body."""
        if body is None:
            return True
        for entry in body:
            if not entry.check_valid_ros_instantiations(ros_declarations):
                return False
        return True

    def _convert_ros_instantiations_to_plain_scxml(
            body: List[ScxmlBase], ros_declarations: HelperRosDeclarations) -> List[ScxmlBase]:
        """Convert the ROS-specific entries to be plain SCXML"""
        if body is None:
            return
        converted_body = []
        for entry in body:
            converted_body.append(entry.as_plain_scxml(ros_declarations))

    def as_plain_scxml(self, ros_declarations: HelperRosDeclarations) -> "ScxmlState":
        """Convert the ROS-specific entries to be plain SCXML"""
        plain_entry = ScxmlState._convert_ros_instantiations_to_plain_scxml(
            self._on_entry, ros_declarations)
        plain_exit = ScxmlState._convert_ros_instantiations_to_plain_scxml(
            self._on_exit, ros_declarations)
        plain_body = ScxmlState._convert_ros_instantiations_to_plain_scxml(
            self._body, ros_declarations)
        return ScxmlState(self._id, on_entry=plain_entry, on_exit=plain_exit, body=plain_body)

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
