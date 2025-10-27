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

from typing import Dict, List, Optional, Type, Union

from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.logging import get_error_msg
from as2fm.scxml_converter.ascxml_extensions import AscxmlDeclaration, AscxmlThread
from as2fm.scxml_converter.ascxml_extensions.bt_entries import BtPortsHandler
from as2fm.scxml_converter.ascxml_extensions.ros_entries import (
    RosActionServer,
    RosCallback,
    RosField,
    RosTrigger,
    ScxmlRosDeclarationsContainer,
)
from as2fm.scxml_converter.ascxml_extensions.ros_entries.ros_utils import (
    generate_action_thread_execution_start_event,
    generate_action_thread_free_event,
    sanitize_ros_interface_name,
)
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import (
    ScxmlBase,
    ScxmlDataModel,
    ScxmlParam,
    ScxmlRoot,
    ScxmlState,
    ScxmlTransition,
    ScxmlTransitionTarget,
)
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import (
    PLAIN_SCXML_EVENT_DATA_PREFIX,
    CallbackType,
    is_non_empty_string,
)
from as2fm.scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok,
    get_children_as_scxml,
    get_xml_attribute,
)


class RosActionThread(AscxmlThread):
    """
    SCXML declaration of a set of threads for executing the action server code.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_thread"

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, custom_data_types: Dict[str, StructDefinition]
    ) -> "RosActionThread":
        """Create a RosActionThread object from an XML tree."""
        assert_xml_tag_ok(RosActionThread, xml_tree)
        action_alias = get_xml_attribute(RosActionThread, xml_tree, "name")
        n_threads = get_xml_attribute(RosActionThread, xml_tree, "n_threads")
        n_threads = int(n_threads)
        assert n_threads > 0, f"Error: SCXML Action Thread: invalid n. of threads ({n_threads})."
        initial_state = get_xml_attribute(RosActionThread, xml_tree, "initial")
        datamodel = get_children_as_scxml(xml_tree, custom_data_types, (ScxmlDataModel,))
        # ros declarations and bt ports are expected to be defined in the parent tag (scxml_root)
        scxml_states: List[ScxmlState] = get_children_as_scxml(
            xml_tree, custom_data_types, (ScxmlState,)
        )
        assert len(datamodel) <= 1, "Error: SCXML Action Thread: multiple datamodels."
        assert len(scxml_states) > 0, "Error: SCXML Action Thread: no states defined."
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
        self._data_model: Optional[ScxmlDataModel] = None
        self._states: List[ScxmlState] = []

    def add_state(self, state: ScxmlState, *, initial: bool = False):
        """Append a state to the list of states of the thread.
        If initial is True, set it as the initial state."""
        self._states.append(state)
        if initial:
            assert self._initial_state is None, "Error: RosActionThread: Initial state already set"
            self._initial_state = state.get_id()

    def set_data_model(self, data_model: ScxmlDataModel):
        assert self._data_model is None, "Data model already set"
        self._data_model = data_model

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler) -> None:
        if self._data_model is not None:
            self._data_model.update_bt_ports_values(bt_ports_handler)
        for state in self._states:
            state.update_bt_ports_values(bt_ports_handler)

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosActionThread, "name", self._name)
        valid_n_threads = isinstance(self._n_threads, int) and self._n_threads > 0
        valid_initial_state = self._initial_state is not None
        valid_data_model = self._data_model is None or self._data_model.check_validity()
        valid_states = all(
            isinstance(state, ScxmlState) and state.check_validity() for state in self._states
        )
        if not valid_name:
            return False
        if not valid_n_threads:
            print(
                "Error: SCXML RosActionThread: "
                f"{self._name} has invalid n_threads ({self._n_threads})."
            )
        if not valid_initial_state:
            print(f"Error: SCXML RosActionThread: {self._name} has no initial state.")
        if not valid_data_model:
            print(f"Error: SCXML RosActionThread: {self._name} has an invalid datamodel.")
        if not valid_states:
            print(f"Error: SCXML RosActionThread: {self._name} has invalid states.")
        return valid_n_threads and valid_initial_state and valid_data_model and valid_states

    def check_valid_ros_instantiations(self, ros_decls: ScxmlRosDeclarationsContainer) -> bool:
        assert isinstance(
            ros_decls, ScxmlRosDeclarationsContainer
        ), "Error: SCXML RosActionThread: Invalid ROS declarations container."
        if not ros_decls.is_action_server_defined(self._name):
            print(f"Error: SCXML RosActionThread: undeclared thread action server '{self._name}'.")
            return False
        if not all(state.check_valid_ros_instantiations(ros_decls) for state in self._states):
            print(
                "Error: SCXML RosActionThread: "
                f"invalid ROS instantiation for states in thread '{self._name}'."
            )
            return False
        return True

    def _find_action_name(self, ascxml_declarations: List[AscxmlDeclaration]) -> str:
        for decl in ascxml_declarations:
            if isinstance(decl, RosActionServer) and decl.get_name() == self._name:
                return decl.get_interface_name()
        raise RuntimeError(
            get_error_msg(
                self.get_xml_origin(), f"Cannot find declaration of action server {self._name}"
            )
        )

    def as_plain_scxml(
        self,
        struct_declarations: Optional[ScxmlStructDeclarationsContainer],
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> List[ScxmlBase]:
        """
        Convert the ROS-specific entries to be plain SCXML.

        This returns a list of ScxmlRoot objects, using ScxmlBase to avoid circular dependencies.
        """

        # This is an independent automaton, no structs shall be provided from outside.
        assert struct_declarations is None, "Unexpected struct_declarations. Should be None."
        assert self._data_model is not None, "No datamodel found in the thread."

        struct_declarations = ScxmlStructDeclarationsContainer(
            self._name, self._data_model, self.get_custom_data_types()
        )

        thread_instances: List[ScxmlBase] = []
        action_name = sanitize_ros_interface_name(self._find_action_name(ascxml_declarations))
        for thread_idx in range(self._n_threads):
            thread_name = f"{action_name}_thread_{thread_idx}"
            plain_thread_instance = ScxmlRoot(thread_name)
            plain_thread_instance.set_data_model(self._data_model)
            for state in self._states:
                initial_state = state.get_id() == self._initial_state
                plain_states = state.as_plain_scxml(
                    struct_declarations, ascxml_declarations, thread_id=thread_idx
                )
                assert len(plain_states) == 1, "A state must also be one state in Plain SCXML"
                plain_thread_instance.add_state(plain_states[0], initial=initial_state)
            assert plain_thread_instance.is_plain_scxml(), (
                "Error: SCXML RosActionThread: "
                f"failed to generate a plain-SCXML instance from thread '{self._name}'"
            )
            thread_instances.append(plain_thread_instance)
        return thread_instances

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), "SCXML: found invalid state object."
        # TODO
        raise NotImplementedError("Export of AscxmlROSThreads in XML not done yet.")


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

    @staticmethod
    def get_callback_type() -> CallbackType:
        # The thread is started upon a goal request, so use the action goal type
        return CallbackType.ROS_ACTION_GOAL

    def __init__(
        self,
        server_alias: Union[str, RosActionServer],
        targets: List[ScxmlTransitionTarget],
        condition: Optional[str] = None,
    ) -> None:
        """
        Initialize a new RosActionHandleResult object.

        :param server_alias: Action Server used by this handler, or its name.
        :param targets: A list of targets reachable when after the start trigger is received.
        :param condition: Condition to be met for the callback to be executed. Expected None.
        """
        super().__init__(server_alias, targets, condition)
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
        assert (
            isinstance(thread_id, int) and thread_id >= 0
        ), f"Error: SCXML {self.__class__.__name__}: invalid thread ID ({thread_id})."
        self._thread_id = thread_id
        super().set_thread_id(thread_id)

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_thread_execution_start_event(
            ros_declarations.get_action_server_info(self._interface_name)[0]
        )

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ros_declarations: ScxmlRosDeclarationsContainer,
    ) -> List[ScxmlTransition]:
        assert (
            self._thread_id is not None
        ), f"Error: SCXML {self.__class__.__name__}: thread ID not set."
        # Append a condition checking the thread ID matches the request
        plain_transitions = super().as_plain_scxml(struct_declarations, ros_declarations)
        assert (
            len(plain_transitions) == 1
        ), "A transition must also be one transition in Plain SCXML"
        plain_transitions[0]._condition = (
            f"{PLAIN_SCXML_EVENT_DATA_PREFIX}thread_id == {self._thread_id}"
        )
        return plain_transitions


class RosActionThreadFree(RosTrigger):
    """
    SCXML object receiving a trigger from the action server to stop a thread.

    The selection of the thread is encoded in the event name.
    The thread ID is set from the parent, via a dedicated method.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_thread_free"

    @staticmethod
    def get_declaration_type() -> Type[RosActionServer]:
        return RosActionServer

    def __init__(
        self,
        action_name: Union[str, RosActionServer],
        fields: Optional[List[RosField]] = None,
        _=None,
    ) -> None:
        super().__init__(action_name, fields)
        self._thread_id: Optional[int] = None

    def check_validity(self) -> bool:
        if len(self._fields) > 0:
            print("Error: SCXML RosActionThreadFree: no fields expected.")
            return False
        return super().check_validity()

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_action_server_defined(self._interface_name)

    def check_fields_validity(self, _) -> bool:
        return len(self._fields) == 0

    def set_thread_id(self, thread_id: int) -> None:
        """Set the thread ID for this handler."""
        # The thread ID is expected to be overwritten every time a new thread is generated.
        assert (
            isinstance(thread_id, int) and thread_id >= 0
        ), f"Error: SCXML {self.__class__.__name__}: invalid thread ID ({thread_id})."
        self._thread_id = thread_id

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_thread_free_event(
            ros_declarations.get_action_server_info(self._interface_name)[0]
        )

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ros_declarations: ScxmlRosDeclarationsContainer,
    ) -> List[ScxmlTransition]:
        assert (
            self._thread_id is not None
        ), f"Error: SCXML {self.__class__.__name__}: thread ID not set."
        plain_triggers = super().as_plain_scxml(struct_declarations, ros_declarations)
        assert len(plain_triggers) == 1, "A trigger must also be one trigger in Plain SCXML"
        # Add the thread id to the (empty) param list
        plain_triggers[0].append_param(ScxmlParam("thread_id", expr=str(self._thread_id)))
        return plain_triggers
