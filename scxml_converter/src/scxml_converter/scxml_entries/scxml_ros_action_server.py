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

from scxml_converter.scxml_entries import (
    RosField, ScxmlBase, ScxmlExecutionBody, ScxmlSend, ScxmlTransition,
    as_plain_execution_body, execution_body_from_xml, valid_execution_body)
from scxml_converter.scxml_entries.utils import (
    generate_action_goal_handle_event, is_action_type_known, generate_action_feedback_event,
    generate_action_result_event)
from scxml_converter.scxml_converter import ScxmlRosDeclarationsContainer


class RosActionServer(ScxmlBase):
    """Object used in SCXML root to declare a new action server."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_server"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionServer":
        """Create a RosActionServer object from an XML tree."""
        assert xml_tree.tag == RosActionServer.get_tag_name(), \
            f"Error: SCXML Action Server: XML tag name is not '{RosActionServer.get_tag_name()}'."
        action_name = xml_tree.attrib.get("action_name")
        action_type = xml_tree.attrib.get("type")
        assert action_name is not None and action_type is not None, \
            "Error: SCXML Action Server: 'action_name' or 'type' cannot be found in input xml."
        return RosActionServer(action_name, action_type)

    def __init__(self, action_name: str, action_type: str) -> None:
        """
        Initialize a new RosActionServer object.

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
            print("Error: SCXML Action Server: action name is not valid.")
        if not valid_type:
            print("Error: SCXML Action Server: action type is not valid.")
        return valid_name and valid_type

    def as_plain_scxml(self, _) -> ScxmlBase:
        # This is discarded in the to_plain_scxml_and_declarations method from ScxmlRoot
        raise RuntimeError("Error: SCXML ROS declarations cannot be converted to plain SCXML.")

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Action Server: invalid parameters."
        xml_action_server = ET.Element(
            RosActionServer.get_tag_name(),
            {"action_name": self._action_name, "type": self._action_type})
        return xml_action_server


class RosActionHandleGoal(ScxmlTransition):
    """SCXML object representing a ROS action callback on the server, acting upon a goal."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_handle_goal"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionHandleGoal":
        """Create a RosActionServer object from an XML tree."""
        assert xml_tree.tag == RosActionHandleGoal.get_tag_name(), \
            "Error: SCXML action goal handler: XML tag name is not " +\
            RosActionHandleGoal.get_tag_name()
        action_name = xml_tree.attrib.get("action_name")
        target_name = xml_tree.attrib.get("target")
        assert action_name is not None and target_name is not None, \
            "Error: SCXML action goal handler: 'action_name' or 'target' attribute not " \
            "found in input xml."
        exec_body = execution_body_from_xml(xml_tree)
        return RosActionHandleGoal(action_name, target_name, exec_body)

    def __init__(self, action_decl: Union[str, RosActionServer], target: str,
                 body: Optional[ScxmlExecutionBody] = None) -> None:
        """
        Initialize a new RosActionHandleGoal object.

        :param action_decl: The action server declaration, or its name.
        :param target: Target state after the goal has been received.
        :param body: Execution body to be executed upon goal, before transitioning to target.
        """
        if isinstance(action_decl, RosActionServer):
            self._action_name = action_decl.get_action_name()
        else:
            # Used for generating ROS entries from xml file
            assert isinstance(action_decl, str), \
                "Error: SCXML Action Handle Goal: invalid action name."
            self._action_name = action_decl
        self._target = target
        self._body = body
        assert self.check_validity(), "Error: SCXML Action Handle Goal: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = isinstance(self._action_name, str) and len(self._action_name) > 0
        valid_target = isinstance(self._target, str) and len(self._target) > 0
        valid_body = self._body is None or valid_execution_body(self._body)
        if not valid_name:
            print("Error: SCXML Action Handle Goal: action name is not valid.")
        if not valid_target:
            print("Error: SCXML Action Handle Goal: target is not valid.")
        if not valid_body:
            print("Error: SCXML Action Handle Goal: body is not valid.")
        return valid_name and valid_target and valid_body

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML action goal handler: invalid ROS declarations container."
        action_server_declared = ros_declarations.is_action_server_defined(self._action_name)
        if not action_server_declared:
            print("Error: SCXML action goal handler: "
                  f"action server {self._action_name} not declared.")
            return False
        valid_body = super().check_valid_ros_instantiations(ros_declarations)
        if not valid_body:
            print("Error: SCXML action goal handler: body has invalid ROS instantiations.")
        return valid_body

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlTransition:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML action goal handler: invalid ROS instantiations."
        event_name = generate_action_goal_handle_event(self._action_name)
        target = self._target
        body = as_plain_execution_body(self._body, ros_declarations)
        return ScxmlTransition(target, [event_name], None, body)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Action Handle Goal: invalid parameters."
        xml_action_goal = ET.Element(RosActionHandleGoal.get_tag_name(),
                                     {"action_name": self._action_name, "target": self._target})
        if self._body is not None:
            for body_elem in self._body:
                xml_action_goal.append(body_elem.as_xml())
        return xml_action_goal


class RosActionSendFeedback(ScxmlSend):
    """SCXML object representing the result from a action server."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_feedback"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionSendFeedback":
        """Create a RosActionServer object from an XML tree."""
        assert xml_tree.tag == RosActionSendFeedback.get_tag_name(), \
            "Error: SCXML action feedback: XML tag name is not " + \
            RosActionSendFeedback.get_tag_name()
        action_name = xml_tree.attrib.get("action_name")
        assert action_name is not None, \
            "Error: SCXML action feedback: 'action_name' attribute not found in input xml."
        fields: Optional[List[RosField]] = []
        assert fields is not None, "Error: SCXML action feedback: fields is not valid."
        for field_xml in xml_tree:
            fields.append(RosField.from_xml_tree(field_xml))
        if len(fields) == 0:
            fields = None
        return RosActionSendFeedback(action_name, fields)

    def __init__(self, action_name: Union[str, RosActionServer],
                 fields: Optional[List[RosField]]) -> None:
        """
        Initialize a new RosActionClient object.

        :param action_name: Topic used by the action.
        :param fields: List of fields to be sent in the result.
        """
        if isinstance(action_name, RosActionServer):
            self._action_name = action_name.get_action_name()
        else:
            # Used for generating ROS entries from xml file
            assert isinstance(action_name, str), \
                "Error: SCXML action feedback: invalid action name."
            self._action_name = action_name
        self._fields = fields if fields is not None else []
        assert self.check_validity(), "Error: SCXML action feedback: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = isinstance(self._action_name, str) and len(self._action_name) > 0
        valid_fields = self._fields is None or \
            all([isinstance(field, RosField) and field.check_validity() for field in self._fields])
        if not valid_name:
            print("Error: SCXML action feedback: action name is not valid.")
        if not valid_fields:
            print("Error: SCXML action feedback: fields are not valid.")
        return valid_name and valid_fields

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML action feedback: invalid ROS declarations container."
        action_declared = ros_declarations.is_action_server_defined(self._action_name)
        if not action_declared:
            print("Error: SCXML action feedback: "
                  f"action server {self._action_name} not declared.")
            return False
        valid_fields = ros_declarations.check_valid_action_feedback_fields(
            self._action_name, self._fields)
        if not valid_fields:
            print("Error: SCXML action feedback: invalid fields in result.")
            return False
        return True

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlSend:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML action feedback: invalid ROS instantiations."
        event_name = generate_action_feedback_event(self._action_name)
        # TODO: The result must contain the goal-id field, too!
        event_params = [field.as_plain_scxml(ros_declarations) for field in self._fields]
        return ScxmlSend(event_name, event_params)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML action feedback: invalid parameters."
        xml_action_result = ET.Element(RosActionSendFeedback.get_tag_name(),
                                       {"action_name": self._action_name})
        if self._fields is not None:
            for field in self._fields:
                xml_action_result.append(field.as_xml())
        return xml_action_result


class RosActionSendSucceed(ScxmlSend):
    """SCXML object representing the successful result computation from the action server."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_succeed"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionSendSucceed":
        """Create a RosActionSendSucceed object from an XML tree."""
        assert xml_tree.tag == RosActionSendSucceed.get_tag_name(), \
            "Error: SCXML action succeed result: XML tag name is not " + \
            RosActionSendSucceed.get_tag_name()
        action_name = xml_tree.attrib.get("action_name")
        assert action_name is not None, \
            "Error: SCXML action succeed result: 'action_name' attribute not found in input xml."
        fields: Optional[List[RosField]] = []
        assert fields is not None, "Error: SCXML action succeed result: fields is not valid."
        for field_xml in xml_tree:
            fields.append(RosField.from_xml_tree(field_xml))
        if len(fields) == 0:
            fields = None
        return RosActionSendSucceed(action_name, fields)

    def __init__(self, action_name: Union[str, RosActionServer],
                 fields: Optional[List[RosField]]) -> None:
        """
        Initialize a new RosActionClient object.

        :param action_name: Topic used by the action.
        :param fields: List of fields to be sent in the result.
        """
        if isinstance(action_name, RosActionServer):
            self._action_name = action_name.get_action_name()
        else:
            # Used for generating ROS entries from xml file
            assert isinstance(action_name, str), \
                "Error: SCXML Action Send Result: invalid action name."
            self._action_name = action_name
        self._fields = fields if fields is not None else []
        assert self.check_validity(), "Error: SCXML Action Send Result: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = isinstance(self._action_name, str) and len(self._action_name) > 0
        valid_fields = self._fields is None or \
            all([isinstance(field, RosField) and field.check_validity() for field in self._fields])
        if not valid_name:
            print("Error: SCXML action succeed result: action name is not valid.")
        if not valid_fields:
            print("Error: SCXML action succeed result: fields are not valid.")
        return valid_name and valid_fields

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML action succeed result: invalid ROS declarations container."
        action_declared = ros_declarations.is_action_server_defined(self._action_name)
        if not action_declared:
            print("Error: SCXML action succeed result: "
                  f"action server {self._action_name} not declared.")
            return False
        valid_fields = ros_declarations.check_valid_action_result_fields(
            self._action_name, self._fields)
        if not valid_fields:
            print("Error: SCXML action succeed result: invalid fields in result.")
            return False
        return True

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlSend:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML action succeed result: invalid ROS instantiations."
        event_name = generate_action_result_event(self._action_name)
        # TODO: The result must contain the goal-id field, too!
        event_params = [field.as_plain_scxml(ros_declarations) for field in self._fields]
        return ScxmlSend(event_name, event_params)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Action Send Result: invalid parameters."
        xml_action_result = ET.Element(RosActionSendSucceed.get_tag_name(),
                                       {"action_name": self._action_name})
        if self._fields is not None:
            for field in self._fields:
                xml_action_result.append(field.as_xml())
        return xml_action_result
