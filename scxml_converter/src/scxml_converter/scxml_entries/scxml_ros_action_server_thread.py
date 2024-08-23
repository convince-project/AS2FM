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

from typing import List, Optional, Type, Union
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import (
    ScxmlBase, ScxmlDataModel, ScxmlExecutionBody, ScxmlState, ScxmlRosDeclarationsContainer,
    ScxmlTransition)
from scxml_converter.scxml_entries.scxml_ros_action_server import RosActionServer
from scxml_converter.scxml_entries.scxml_ros_base import RosCallback, RosTrigger

from scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from scxml_converter.scxml_entries.ros_utils import (
    generate_action_thread_execution_start_event)
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
        self._n_threads: int = n_threads
        self._initial_state: Optional[str] = None
        self._datamodel: Optional[ScxmlDataModel] = None
        self._states: List[ScxmlState] = []

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
        if self._datamodel is not None:
            self._datamodel.update_bt_ports_values(bt_ports_handler)
        for state in self._states:
            state.update_bt_ports_values(bt_ports_handler)

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosActionThread, "name", self._name)
        valid_n_threads = isinstance(self._n_threads, int) and self._n_threads > 0
        valid_initial_state = self._initial_state is not None
        valid_datamodel = self._datamodel is None or self._datamodel.check_validity()
        valid_states = all(isinstance(state, ScxmlState) and state.check_validity()
                           for state in self._states)
        if not valid_name:
            return False
        if not valid_n_threads:
            print("Error: SCXML RosActionThread: "
                  f"{self._name} has invalid n_threads ({self._n_threads}).")
        if not valid_initial_state:
            print(f"Error: SCXML RosActionThread: {self._name} has no initial state.")
        if not valid_datamodel:
            print(f"Error: SCXML RosActionThread: {self._name} nas an invalid datamodel.")
        if not valid_states:
            print(f"Error: SCXML RosActionThread: {self._name} has invalid states.")
        return valid_n_threads and valid_initial_state and valid_datamodel and valid_states

    def check_valid_ros_instantiations(self, ros_decls: ScxmlRosDeclarationsContainer) -> bool:
        assert isinstance(ros_decls, ScxmlRosDeclarationsContainer), \
            "Error: SCXML RosActionThread: Invalid ROS declarations container."
        if not ros_decls.is_action_server_defined(self._name):
            print(f"Error: SCXML RosActionThread: undeclared thread action server '{self._name}'.")
            return False
        if not all(state.check_valid_ros_instantiations(ros_decls) for state in self._states):
            print("Error: SCXML RosActionThread: "
                  f"invalid ROS instantiation for states in thread '{self._name}'.")
            return False
        return True

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> List[ScxmlBase]:
        """
        Convert the ROS-specific entries to be plain SCXML.

        This returns a list of ScxmlRoot objects, using ScxmlBase to avoid circular dependencies.
        """
        from scxml_converter.scxml_entries import ScxmlRoot
        thread_instances: List[ScxmlRoot] = []
        action_name = ros_declarations.get_action_server_info(self._name)[0]
        for thread_idx in range(self._n_threads):
            thread_name = f"{action_name}_thread_{thread_idx}"
            plain_thread_instance = ScxmlRoot(thread_name)
            plain_thread_instance.set_data_model(self._datamodel)
            for state in self._states:
                initial_state = state.get_id() == self._initial_state
                state.set_thread_id(thread_idx)
                plain_thread_instance.add_state(state.as_plain_scxml(ros_declarations),
                                                initial=initial_state)
            assert plain_thread_instance.is_plain_scxml(), \
                "Error: SCXML RosActionThread: " \
                f"failed to generate a plain-SCXML instance from thread '{self._name}'"
            thread_instances.append(plain_thread_instance)
        return [thread_instances]

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
        return "ros_action_handle_thread_start"

    @staticmethod
    def get_declaration_type() -> Type[RosActionServer]:
        return RosActionServer

    def __init__(self, server_alias: Union[str, RosActionServer], target_state: str,
                 condition: Optional[str] = None, exec_body: Optional[ScxmlExecutionBody] = None
                 ) -> None:
        """
        Initialize a new RosActionHandleResult object.

        :param server_alias: Action Server used by this handler, or its name.
        :param target_state: Target state to transition to after the start trigger is received.
        :param condition: Condition to be met for the callback to be executed. Expected None.
        :param exec_body: Execution body to be executed upon thread start (before transition).
        """
        super().__init__(server_alias, target_state, condition, exec_body)
        # The thread ID depends on the plain scxml instance, so it is set later
        self._thread_id: Optional[int] = None

    def check_validity(self) -> bool:
        # A condition for the thread start will be autogenerated. Avoid having more than one
        if self._condition is not None:
            print("Error: SCXML RosActionHandleThreadStart: no condition expected.")
            return False
        return super().check_validity()

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the action server has been declared."""
        return ros_declarations.is_action_server_defined(self._interface_name)

    def set_thread_id(self, thread_id: int) -> None:
        """Set the thread ID for this handler."""
        # The thread ID is expected to be overwritten every time a new thread is generated.
        assert isinstance(thread_id, int) and thread_id >= 0, \
            f"Error: SCXML {self.__class__}: invalid thread ID ({thread_id})."
        self._thread_id = thread_id

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_thread_execution_start_event(
            ros_declarations.get_action_server_info(self._interface_name)[0])

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlTransition:
        assert self._thread_id is not None, f"Error: SCXML {self.__class__}: thread ID not set."
        # Append a condition checking the thread ID matches the request
        self._condition = "_req.thread_id == " + str(self._thread_id)
        return super().as_plain_scxml(ros_declarations)


class RosActionThreadFree(RosTrigger):
    """
    SCXML object receiving a trigger from the action server to stop a thread.

    The selection of the thread is encoded in the event name.
    The thread ID is set from the parent, via a dedicated method.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_thread_free"
