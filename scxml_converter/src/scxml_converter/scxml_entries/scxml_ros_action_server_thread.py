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

from typing import List, Optional, Tuple, Type, Union
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import (
    ScxmlBase, ScxmlDataModel, ScxmlExecutionBody, ScxmlState, ScxmlRosDeclarationsContainer,
    execution_body_from_xml)
from scxml_converter.scxml_entries.scxml_ros_action_server import RosActionServer
from scxml_converter.scxml_entries.scxml_ros_base import RosCallback

from scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from scxml_converter.scxml_entries.ros_utils import generate_action_thread_execution_start_event
from scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok, get_xml_argument, get_children_as_scxml)
from scxml_converter.scxml_entries.utils import is_non_empty_string


class RosActionThread(ScxmlBase):
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
        self._name: str = ""
        if isinstance(action_server, RosActionServer):
            self._name = action_server.get_name()
        else:
            assert is_non_empty_string(RosActionThread, "name", action_server)
            self._name = action_server
        self._n_threads = n_threads
        self._initial_state: Optional[str] = None
        self._datamodel: Optional[ScxmlDataModel] = None
        self._states: List[Tuple[ScxmlState, bool]] = []

    def add_state(self, state: ScxmlState, *, initial: bool = False):
        """Append a state to the list of states. If initial is True, set it as the initial state."""
        self._states.append(state)
        if initial:
            assert self._initial_state is None, "Error: SCXML root: Initial state already set"
            self._initial_state = state.get_id()

    def set_data_model(self, data_model: ScxmlDataModel):
        assert self._data_model is None, "Data model already set"
        self._data_model = data_model

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler) -> None:
        # TODO
        pass

    def check_validity(self) -> bool:
        # TODO
        pass

    def check_valid_ros_instantiations(self, ros_declarations: ScxmlRosDeclarationsContainer
                                       ) -> bool:
        # TODO
        pass

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> List[ScxmlBase]:
        """
        Convert the ROS-specific entries to be plain SCXML.

        This returns a list of ScxmlRoot objects, using ScxmlBase to avoid circular dependencies.
        """
        from scxml_converter.scxml_entries import ScxmlRoot
        # TODO
        return [ScxmlRoot("name")]

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid state object."
        # TODO
        pass


class RosActionHandleThreadStart(RosCallback):
    """
    SCXML object receiving a trigger from the action server to start a thread.

    The selection of the thread is encoded in the event name.
    The thread ID is set from the parent, via a dedicated method.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_thread_start"

    @staticmethod
    def get_declaration_type() -> Type[RosActionServer]:
        return RosActionServer

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionHandleThreadStart":
        """Create a RosActionHandleThreadStart object from an XML tree."""
        assert_xml_tag_ok(RosActionHandleThreadStart, xml_tree)
        server_alias = get_xml_argument(RosActionHandleThreadStart, xml_tree, "name")
        target_state = get_xml_argument(RosActionHandleThreadStart, xml_tree, "target")
        exec_body = execution_body_from_xml(xml_tree)
        return RosActionHandleThreadStart(server_alias, target_state, exec_body)

    def __init__(self, server_alias: Union[str, RosActionServer], target_state: str,
                 exec_body: Optional[ScxmlExecutionBody] = None) -> None:
        """
        Initialize a new RosActionHandleResult object.

        :param server_alias: Action Server used by this handler, or its name.
        :param target_state: Target state to transition to after the start trigger is received.
        :param exec_body: Execution body to be executed upon thread start (before transition).
        """
        super().__init__(server_alias, target_state, exec_body)
        # The thread ID depends on the plain scxml instance, so it is set later
        self._thread_id: Optional[str] = None

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the action server has been declared."""
        return ros_declarations.is_action_server_defined(self._interface_name)

    def set_thread_id(self, thread_id: str) -> None:
        """Set the thread ID for this handler."""
        assert self._thread_id is None, f"Error: SCXML {self.__class__}: thread ID set."
        is_non_empty_string(self.__class__, "thread_id", thread_id)
        self._thread_id = thread_id

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_thread_execution_start_event(
            ros_declarations.get_action_server_info(self._interface_name)[0], self._thread_id)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), f"Error: SCXML {self.__class__}: invalid parameters."
        xml_thread_start = ET.Element(self.get_tag_name(),
                                      {"name": self._interface_name, "target": self._target})
        if self._body is not None:
            for body_elem in self._body:
                xml_thread_start.append(body_elem.as_xml())
        return xml_thread_start


class RosActionHandleThreadCancel(RosActionHandleThreadStart):
    """
    SCXML object receiving a trigger from the action server to stop a thread.

    The selection of the thread is encoded in the event name.
    The thread ID is set from the parent, via a dedicated method.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_thread_cancel"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionHandleThreadCancel":
        """Create a RosActionHandleThreadCancel object from an XML tree."""
        assert_xml_tag_ok(RosActionHandleThreadCancel, xml_tree)
        server_alias = get_xml_argument(RosActionHandleThreadCancel, xml_tree, "name")
        target_state = get_xml_argument(RosActionHandleThreadCancel, xml_tree, "target")
        exec_body = execution_body_from_xml(xml_tree)
        return RosActionHandleThreadCancel(server_alias, target_state, exec_body)

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_thread_execution_start_event(
            ros_declarations.get_action_server_info(self._interface_name)[0], self._thread_id)
