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
Declaration of SCXML tags related to ROS Action Clients.

Based loosely on https://design.ros2.org/articles/actions.html
"""

from typing import List, Optional, Tuple, Union, get_args
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import (
    ScxmlRoot, ScxmlDataModel, ScxmlExecutionBody, ScxmlState, ScxmlTransition,
    ScxmlRosDeclarationsContainer, as_plain_execution_body,
    execution_body_from_xml, valid_execution_body)
from scxml_converter.scxml_entries.scxml_ros_action_server import RosActionServer

from scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok, get_xml_argument, get_children_as_scxml)
from scxml_converter.scxml_entries.utils import is_non_empty_string


class RosActionThread(ScxmlRoot):
    """
    SCXML declaration of a set of threads for executing the action server code.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_thread"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionThread":
        """Create a RosActionThread object from an XML tree."""
        assert_xml_tag_ok(RosActionThread, xml_tree)
        action_alias = get_xml_argument(RosActionThread, xml_tree, "name")
        n_threads = get_xml_argument(RosActionThread, xml_tree, "n_threads")
        n_threads = int(n_threads)
        assert n_threads > 0, f"Error: SCXML Action Thread: invalid n. of threads ({n_threads})."
        initial_state = get_xml_argument(RosActionThread, xml_tree, "initial_state")
        datamodel = get_children_as_scxml(xml_tree, (ScxmlDataModel,))
        # ros declarations and bt ports are expected to be defined in the parent tag (scxml_root)
        scxml_states: List[ScxmlState] = get_children_as_scxml(xml_tree, (ScxmlState,))
        assert len(datamodel) <= 1, "Error: SCXML Action Thread: multiple datamodels."
        assert scxml_states > 0, "Error: SCXML Action Thread: no states defined."
        # The non-plain SCXML Action thread has the same name as the action
        scxml_action_thread = RosActionThread(action_alias, n_threads)
        # Fill the thread with the states and datamodel
        if len(datamodel) == 1:
            scxml_action_thread.set_data_model(datamodel[0])
        for scxml_state in scxml_states:
            is_initial = scxml_state.get_id() == initial_state
            scxml_action_thread.add_state(scxml_state, initial=is_initial)
        return scxml_action_thread

    @staticmethod
    def from_scxml_file(_):
        raise RuntimeError("Error: Cannot load a RosActionThread directly from SCXML file.")

    def __init__(self, action_server: Union[str, RosActionServer], n_threads: int) -> None:
        """
        Initialize a new RosActionThread object.

        :param action_server: ActionServer declaration, or its alias name.
        :param n_threads: Max. n. of parallel action requests that can be handled.
        """
        if isinstance(action_server, RosActionServer):
            action_name = action_server.get_name()
        else:
            assert is_non_empty_string(RosActionThread, "name", action_server)
            action_name = action_server
        self._n_threads = n_threads
        super().__init__(action_name)
        del self._ros_declarations  # The ROS declarations should be externally provided
        del self._bt_ports_handler  # The BT ports should be externally provided

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler) -> None:
        # TODO
        pass

    def check_validity(self) -> bool:
        # TODO
        pass

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        # TODO
        pass

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> List[ScxmlRoot]:
        """Convert the ROS-specific entries to be plain SCXML"""
        # TODO
        pass

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid state object."
        # TODO
        pass

    # Disable a bunch of unneeded methods
    def instantiate_bt_events(self, _) -> None:
        raise RuntimeError("Error: SCXML Action Thread: deleted method 'instantiate_bt_events'.")

    def add_ros_declaration(self, _):
        raise RuntimeError("Error: SCXML Action Thread: deleted method 'add_ros_declaration'.")

    def add_bt_port_declaration(self, _):
        raise RuntimeError("Error: SCXML Action Thread: deleted method 'add_bt_port_declaration'.")

    def set_bt_port_value(self, _, __):
        raise RuntimeError("Error: SCXML Action Thread: deleted method 'set_bt_port_values'.")

    def set_bt_ports_values(self, _):
        raise RuntimeError("Error: SCXML Action Thread: deleted method 'set_bt_ports_values'.")

    def _generate_ros_declarations_helper(self):
        raise RuntimeError("Error: SCXML Action Thread: deleted method "
                           "'_generate_ros_declarations_helper'.")

    def _check_valid_ros_declarations(self):
        raise RuntimeError(
            "Error: SCXML Action Thread: deleted method '_check_valid_ros_declarations': "
            "use 'check_valid_ros_instantiations' instead (no underscore).")

    def is_plain_scxml(self):
        raise RuntimeError("Error: SCXML Action Thread: deleted method 'is_plain_scxml'.")

    def to_plain_scxml_and_declarations(self):
        raise RuntimeError("Error: SCXML Action Thread: deleted method "
                           "'to_plain_scxml_and_declarations'.")


class RosActionHandleThreadStart(ScxmlTransition):
    """SCXML object representing the handler of am action result for a service client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_handle_result"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionHandleResult":
        """Create a RosActionHandleResult object from an XML tree."""
        assert_xml_tag_ok(RosActionHandleResult, xml_tree)
        client_name = get_xml_argument(RosActionHandleResult, xml_tree, "name")
        target_name = get_xml_argument(RosActionHandleResult, xml_tree, "target")
        exec_body = execution_body_from_xml(xml_tree)
        return RosActionHandleResult(client_name, target_name, exec_body)

    def __init__(self, action_client: Union[str, RosActionClient], target: str,
                 body: Optional[ScxmlExecutionBody] = None) -> None:
        """
        Initialize a new RosActionHandleResult object.

        :param action_client: Action client used by this handler, or its name.
        :param target: Target state to transition to after the feedback is received.
        :param body: Execution body to be executed upon feedback reception (before transition).
        """
        if isinstance(action_client, RosActionClient):
            self._client_name = action_client.get_name()
        else:
            assert is_non_empty_string(RosActionHandleResult, "name", action_client)
            self._client_name = action_client
        self._target = target
        self._body = body
        assert self.check_validity(), "Error: SCXML RosActionHandleResult: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosActionHandleResult, "name", self._client_name)
        valid_target = is_non_empty_string(RosActionHandleResult, "target", self._target)
        valid_body = self._body is None or valid_execution_body(self._body)
        if not valid_body:
            print("Error: SCXML RosActionHandleResult: body is not valid.")
        return valid_name and valid_target and valid_body

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML RosActionHandleResult: invalid ROS declarations container."
        if not ros_declarations.is_action_client_defined(self._client_name):
            print("Error: SCXML RosActionHandleResult: "
                  f"action client {self._client_name} not declared.")
            return False
        if not super().check_valid_ros_instantiations(ros_declarations):
            print("Error: SCXML RosActionHandleResult: invalid ROS instantiations in exec body.")
            return False
        return True

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlTransition:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML service response handler: invalid ROS instantiations."
        automaton_name = ros_declarations.get_automaton_name()
        interface_name, _ = ros_declarations.get_action_client_info(self._client_name)
        event_name = generate_action_result_handle_event(interface_name, automaton_name)
        target = self._target
        body = as_plain_execution_body(self._body, ros_declarations)
        return ScxmlTransition(target, [event_name], None, body)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML RosActionHandleResult: invalid parameters."
        xml_handle_feedback = ET.Element(RosActionHandleResult.get_tag_name(),
                                         {"name": self._client_name, "target": self._target})
        if self._body is not None:
            for body_elem in self._body:
                xml_handle_feedback.append(body_elem.as_xml())
        return xml_handle_feedback
