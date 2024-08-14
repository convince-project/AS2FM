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
Declaration of SCXML tags related to ROS Actions.

Based loosely on https://design.ros2.org/articles/actions.html.
"""

from typing import List, Optional, Union
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import (RosField, ScxmlBase,
                                           ScxmlExecutionBody, ScxmlSend,
                                           ScxmlTransition,
                                           as_plain_execution_body,
                                           execution_body_from_xml,
                                           valid_execution_body)
from scxml_converter.scxml_entries.utils import (
    is_action_type_known, generate_action_goal_event, generate_action_feedback_handle_event,
    generate_action_result_handle_event)
from scxml_converter.scxml_converter import ScxmlRosDeclarationsContainer


class RosActionClient(ScxmlBase):
    """Object used in SCXML root to declare a new action client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_client"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionClient":
        """Create a RosActionClient object from an XML tree."""
        assert xml_tree.tag == RosActionClient.get_tag_name(), \
            f"Error: SCXML Action Client: XML tag name is not '{RosActionClient.get_tag_name()}'."
        action_name = xml_tree.attrib.get("action_name")
        action_type = xml_tree.attrib.get("type")
        assert action_name is not None and action_type is not None, \
            "Error: SCXML Action Client: 'action_name' or 'type' cannot be found in input xml."
        return RosActionClient(action_name, action_type)

    def __init__(self, action_name: str, action_type: str) -> None:
        """
        Initialize a new RosActionClient object.

        :param action_name: Topic used by the action.
        :param action_type: ROS type of the action.
        """
        self._action_name = action_name
        self._action_type = action_type

    def get_action_name(self) -> str:
        """Get the name of the action."""
        return self._action_name

    def get_action_type(self) -> str:
        """Get the type of the action."""
        return self._action_type

    def check_validity(self) -> bool:
        valid_name = isinstance(self._action_name, str) and len(self._action_name) > 0
        valid_type = is_action_type_known(self._action_type)
        if not valid_name:
            print("Error: SCXML Action Client: action name is not valid.")
        if not valid_type:
            print("Error: SCXML Action Client: action type is not valid.")
        return valid_name and valid_type

    def as_plain_scxml(self, _) -> ScxmlBase:
        # This is discarded in the to_plain_scxml_and_declarations method from ScxmlRoot
        raise RuntimeError("Error: SCXML ROS declarations cannot be converted to plain SCXML.")

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Action Client: invalid parameters."
        xml_action_server = ET.Element(
            RosActionClient.get_tag_name(),
            {"action_name": self._action_name, "type": self._action_type})
        return xml_action_server


class RosActionSendGoal(ScxmlSend):
    """Object representing a ROS action goal (from the client side) in SCXML."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_send_goal"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionSendGoal":
        """Create a RosActionServer object from an XML tree."""
        assert xml_tree.tag == RosActionSendGoal.get_tag_name(), \
            "Error: SCXML action goal: XML tag name is not " + \
            RosActionSendGoal.get_tag_name()
        action_name = xml_tree.attrib.get("action_name")
        assert action_name is not None, \
            "Error: SCXML action goal: 'action_name' attribute not found in input xml."
        fields: List[RosField] = []
        for field_xml in xml_tree:
            fields.append(RosField.from_xml_tree(field_xml))
        return RosActionSendGoal(action_name, fields)

    def __init__(self,
                 action_decl: Union[str, RosActionClient],
                 fields: List[RosField] = None) -> None:
        """
        Initialize a new RosActionSendGoal object.

        :param action_decl: Name of the action of Scxml obj. of Action Client declaration.
        :param fields: List of fields to be sent in the goal.
        """
        if isinstance(action_decl, RosActionClient):
            self._action_name = action_decl.get_action_name()
        else:
            # Used for generating ROS entries from xml file
            assert isinstance(action_decl, str), \
                "Error: SCXML Action Send Goal: invalid action name."
            self._action_name = action_decl
        if fields is None:
            fields = []
        self._fields = fields
        assert self.check_validity(), "Error: SCXML Action Send Goal: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = isinstance(self._action_name, str) and len(self._action_name) > 0
        valid_fields = self._fields is None or \
            all([isinstance(field, RosField) and field.check_validity() for field in self._fields])
        if not valid_name:
            print("Error: SCXML action goal: action name is not valid.")
        if not valid_fields:
            print("Error: SCXML action goal: fields are not valid.")
        return valid_name and valid_fields

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ros instantiations have been declared."""
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML action goal: invalid ROS declarations container."
        action_client_declared = ros_declarations.is_action_client_defined(self._action_name)
        if not action_client_declared:
            print(f"Error: SCXML action goal: action client {self._action_name} not declared.")
            return False
        valid_fields = ros_declarations.check_valid_action_goal_fields(
            self._action_name, self._fields)
        if not valid_fields:
            print("Error: SCXML action goal: invalid fields in goal.")
            return False
        return True

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlSend:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML action goal: invalid ROS instantiations."
        event_name = generate_action_goal_event(
            self._action_name, ros_declarations.get_automaton_name())
        event_params = [field.as_plain_scxml(ros_declarations) for field in self._fields]
        return ScxmlSend(event_name, event_params)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Action Send Goal: invalid parameters."
        xml_action_goal = ET.Element(RosActionSendGoal.get_tag_name(),
                                     {"action_name": self._action_name})
        if self._fields is not None:
            for field in self._fields:
                xml_action_goal.append(field.as_xml())
        return xml_action_goal


class RosActionHandleFeedback(ScxmlTransition):
    """SCXML object representing the handler of an action feedback for an action client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_handle_feedback"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionHandleFeedback":
        """Create a RosActionServer object from an XML tree."""
        assert xml_tree.tag == RosActionHandleFeedback.get_tag_name(), \
            "Error: SCXML action feedback handler: XML tag name is not " + \
            RosActionHandleFeedback.get_tag_name()
        action_name = xml_tree.attrib.get("action_name")
        target_name = xml_tree.attrib.get("target")
        assert action_name is not None and target_name is not None, \
            "Error: SCXML action feedback handler: 'action_name' or 'target' attribute not " \
            "found in input xml."
        exec_body = execution_body_from_xml(xml_tree)
        return RosActionHandleFeedback(action_name, target_name, exec_body)

    def __init__(self, action_decl: Union[str, RosActionClient], target: str,
                 body: Optional[ScxmlExecutionBody] = None) -> None:
        """
        Initialize a new RosActionClient object.

        :param action_name: Topic used by the action.
        :param type: ROS type of the action.
        """
        if isinstance(action_decl, RosActionClient):
            self._action_name = action_decl.get_action_name()
        else:
            # Used for generating ROS entries from xml file
            assert isinstance(action_decl, str), \
                "Error: SCXML Action Handle Feedback: invalid action name."
            self._action_name = action_decl
        self._target = target
        self._body = body
        assert self.check_validity(), "Error: SCXML Action Handle Feedback: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = isinstance(self._action_name, str) and len(self._action_name) > 0
        valid_target = isinstance(self._target, str) and len(self._target) > 0
        valid_body = self._body is None or valid_execution_body(self._body)
        if not valid_name:
            print("Error: SCXML Action Handle Feedback: action name is not valid.")
        if not valid_target:
            print("Error: SCXML Action Handle Feedback: target is not valid.")
        if not valid_body:
            print("Error: SCXML Action Handle Feedback: body is not valid.")
        return valid_name and valid_target and valid_body

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML Action Handle Feedback: invalid ROS declarations container."
        action_declared = ros_declarations.is_action_client_defined(self._action_name)
        if not action_declared:
            print("Error: SCXML Action Handle Feedback: "
                  f"action server {self._action_name} not declared.")
            return False
        valid_body = super().check_valid_ros_instantiations(ros_declarations)
        if not valid_body:
            print("Error: SCXML Action Handle Feedback: body has invalid ROS instantiations.")
        return valid_body

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlTransition:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML action feedback handler: invalid ROS instantiations."
        event_name = generate_action_feedback_handle_event(
            self._action_name, ros_declarations.get_automaton_name())
        target = self._target
        body = as_plain_execution_body(self._body, ros_declarations)
        return ScxmlTransition(target, [event_name], None, body)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Action Handle Feedback: invalid parameters."
        xml_action_feedback = ET.Element(RosActionHandleFeedback.get_tag_name(),
                                         {"action_name": self._action_name, "target": self._target})
        if self._body is not None:
            for body_elem in self._body:
                xml_action_feedback.append(body_elem.as_xml())
        return xml_action_feedback


class RosActionHandleResult(ScxmlTransition):
    """SCXML object representing the handler of an action result for an action client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_handle_result"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionHandleResult":
        """Create a RosActionServer object from an XML tree."""
        assert xml_tree.tag == RosActionHandleResult.get_tag_name(), \
            "Error: SCXML action result handler: XML tag name is not " + \
            RosActionHandleResult.get_tag_name()
        action_name = xml_tree.attrib.get("action_name")
        target_name = xml_tree.attrib.get("target")
        assert action_name is not None and target_name is not None, \
            "Error: SCXML action result handler: 'action_name' or 'target' attribute not " \
            "found in input xml."
        exec_body = execution_body_from_xml(xml_tree)
        return RosActionHandleResult(action_name, target_name, exec_body)

    def __init__(self, action_decl: Union[str, RosActionClient], target: str,
                 body: Optional[ScxmlExecutionBody] = None) -> None:
        """
        Initialize a new RosActionClient object.

        :param action_name: Topic used by the action.
        :param type: ROS type of the action.
        """
        if isinstance(action_decl, RosActionClient):
            self._action_name = action_decl.get_action_name()
        else:
            # Used for generating ROS entries from xml file
            assert isinstance(action_decl, str), \
                "Error: SCXML Action Handle Result: invalid action name."
            self._action_name = action_decl
        self._target = target
        self._body = body
        assert self.check_validity(), "Error: SCXML Action Handle Result: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = isinstance(self._action_name, str) and len(self._action_name) > 0
        valid_target = isinstance(self._target, str) and len(self._target) > 0
        valid_body = self._body is None or valid_execution_body(self._body)
        if not valid_name:
            print("Error: SCXML Action Handle Result: action name is not valid.")
        if not valid_target:
            print("Error: SCXML Action Handle Result: target is not valid.")
        if not valid_body:
            print("Error: SCXML Action Handle Result: body is not valid.")
        return valid_name and valid_target and valid_body

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML Action Handle Result: invalid ROS declarations container."
        action_declared = ros_declarations.is_action_client_defined(self._action_name)
        if not action_declared:
            print("Error: SCXML Action Handle Result: "
                  f"action server {self._action_name} not declared.")
            return False
        valid_body = super().check_valid_ros_instantiations(ros_declarations)
        if not valid_body:
            print("Error: SCXML Action Handle Result: body has invalid ROS instantiations.")
        return valid_body

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlTransition:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML action result handler: invalid ROS instantiations."
        event_name = generate_action_result_handle_event(
            self._action_name, ros_declarations.get_automaton_name())
        target = self._target
        body = as_plain_execution_body(self._body, ros_declarations)
        return ScxmlTransition(target, [event_name], None, body)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Action Handle Result: invalid parameters."
        xml_action_result = ET.Element(RosActionHandleResult.get_tag_name(),
                                       {"action_name": self._action_name, "target": self._target})
        if self._body is not None:
            for body_elem in self._body:
                xml_action_result.append(body_elem.as_xml())
        return xml_action_result
