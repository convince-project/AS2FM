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

"""Collection of SCXML ROS Base classes to derive from."""

from typing import Optional, Union, Type

from scxml_converter.scxml_entries import (
    ScxmlBase, ScxmlTransition, ScxmlExecutionBody, BtGetValueInputPort,
    ScxmlRosDeclarationsContainer, as_plain_execution_body, valid_execution_body)

from scxml_converter.scxml_entries.bt_utils import BtPortsHandler

from scxml_converter.scxml_entries.utils import is_non_empty_string


class RosDeclaration(ScxmlBase):
    """Base class for ROS declarations in SCXML."""

    @classmethod
    def get_tag_name(cls) -> str:
        raise NotImplementedError(f"{cls.__name__} doesn't implement get_tag_name.")

    def __init__(self, interface_name: Union[str, BtGetValueInputPort], interface_type: str,
                 interface_alias: Optional[str] = None):
        """
        Constructor of ROS declaration.

        :param interface_name: Comm. interface used by the declared ROS interface.
        :param interface_type: ROS type used for communication.
        :param interface_alias: Alias for the defined interface, used for ref. by the the handlers
        """
        self._interface_name = interface_name
        self._interface_type = interface_type
        self._interface_alias = interface_alias
        assert isinstance(interface_name, (str, BtGetValueInputPort)), \
            f"Error: SCXML {self.get_tag_name()}: " \
            f"invalid type of interface_name {type(interface_name)}."
        if self._interface_alias is None:
            assert is_non_empty_string(self.__class__, "interface_name", self._interface_name), \
                f"Error: SCXML {self.get_tag_name()}: " \
                "an alias name is required for dynamic ROS interfaces."
            self._interface_alias = interface_name

    def get_interface_name(self) -> str:
        """Get the name of the ROS comm. interface."""
        return self._interface_name

    def get_interface_type(self) -> str:
        """Get the ROS type used for communication."""
        return self._interface_type

    def get_name(self) -> str:
        """Get the alias name of the ROS interface."""
        return self._interface_alias

    def check_valid_interface_type(self) -> bool:
        return NotImplementedError(
            f"{self.__class__.__name__} doesn't implement check_valid_interface_type.")

    def check_validity(self) -> bool:
        valid_alias = is_non_empty_string(self.__class__, "name", self._interface_alias)
        valid_action_name = isinstance(self._interface_name, BtGetValueInputPort) or \
            is_non_empty_string(self.__class__, "interface_name", self._interface_name)
        valid_action_type = self.check_valid_interface_type()
        return valid_alias and valid_action_name and valid_action_type

    def check_valid_instantiation(self) -> bool:
        """Check if the interface name is still undefined (i.e. from BT ports)."""
        return is_non_empty_string(self.__class__, "interface_name", self._interface_name)

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler) -> None:
        """Update the values of potential entries making use of BT ports."""
        if isinstance(self._interface_name, BtGetValueInputPort):
            self._interface_name = \
                bt_ports_handler.get_in_port_value(self._interface_name.get_key_name())

    def as_plain_scxml(self, _) -> ScxmlBase:
        # This is discarded in the to_plain_scxml_and_declarations method from ScxmlRoot
        raise RuntimeError(f"Error: SCXML {self.__class__} cannot be converted to plain SCXML.")


class RosCallback(ScxmlTransition):
    """Base class for ROS callbacks in SCXML."""

    @classmethod
    def get_tag_name(cls) -> str:
        """XML tag name for the ROS callback type."""
        raise NotImplementedError(f"{cls.__name__} doesn't implement get_tag_name.")

    @classmethod
    def get_declaration_type(cls) -> Type[RosDeclaration]:
        """
        Get the type of ROS declaration related to the callback.

        Examples: RosSubscriber, RosPublisher, ...
        """
        raise NotImplementedError(f"{cls.__name__} doesn't implement get_declaration_type.")

    def __init__(self, interface_decl: Union[str, RosDeclaration], target_state: str,
                 exec_body: Optional[ScxmlExecutionBody] = None) -> None:
        """
        Constructor of ROS callback.

        :param interface_decl: ROS interface declaration to be used in the callback, or its name.
        :param target_state: Name of the state to transition to after the callback.
        :param exec_body: Executable body of the callback.
        """
        if isinstance(interface_decl, self.get_declaration_type()):
            self._interface_name = interface_decl.get_name()
        else:
            assert is_non_empty_string(self.__class__, "name", interface_decl)
            self._interface_name = interface_decl
        self._target = target_state
        self._body = exec_body
        assert self.check_validity(), f"Error: SCXML {self.__class__}: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(self.__class__, "name", self._interface_name)
        valid_target = is_non_empty_string(self.__class__, "target", self._target)
        valid_body = self._body is None or valid_execution_body(self._body)
        if not valid_body:
            print(f"Error: SCXML {self.__class__}: invalid entries in executable body.")
        return valid_name and valid_target and valid_body

    def check_valid_interface(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ROS interface used in the callback exists."""
        raise NotImplementedError(
            f"{self.__class__.__name__} doesn't implement check_valid_interface.")

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        """Translate the ROS interface name to a plain scxml event."""
        raise NotImplementedError(
            f"{self.__class__.__name__} doesn't implement get_plain_scxml_event.")

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ROS entries in the callback are correctly defined."""
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            f"Error: SCXML {self.__class__}: invalid type of ROS declarations container."
        if not self.check_valid_interface(ros_declarations):
            print(f"Error: SCXML {self.__class__}: undefined ROS interface {self._interface_name}.")
            return False
        valid_body = super().check_valid_ros_instantiations(ros_declarations)
        if not valid_body:
            print(f"Error: SCXML {self.__class__}: body has invalid ROS instantiations.")
        return valid_body

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlBase:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML topic callback: invalid ROS instantiations."
        event_name = self.get_plain_scxml_event(ros_declarations)
        target = self._target
        body = as_plain_execution_body(self._body, ros_declarations)
        return ScxmlTransition(target, [event_name], None, body)
