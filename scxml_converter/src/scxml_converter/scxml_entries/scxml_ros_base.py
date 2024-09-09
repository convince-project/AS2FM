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

from typing import Dict, Optional, List, Union, Type

from scxml_converter.scxml_entries import (
    BtGetValueInputPort, RosField, ScxmlBase, ScxmlExecutionBody, ScxmlParam,
    ScxmlRosDeclarationsContainer, ScxmlSend, ScxmlTransition)
from scxml_converter.scxml_entries import (
    as_plain_execution_body, execution_body_from_xml, valid_execution_body)

from scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok, get_xml_argument, read_value_from_xml_arg_or_child)
from scxml_converter.scxml_entries.utils import (
    CallbackType, get_plain_expression, is_non_empty_string)

from xml.etree import ElementTree as ET


class RosDeclaration(ScxmlBase):
    """Base class for ROS declarations in SCXML."""

    @classmethod
    def get_tag_name(cls) -> str:
        """The xml tag related to the ROS declaration."""
        raise NotImplementedError(f"{cls.__name__} doesn't implement get_tag_name.")

    @classmethod
    def get_communication_interface(cls) -> str:
        """
        Which communication interface is used by the ROS declaration.

        Expected values: "service", "action"
        """
        raise NotImplementedError(f"{cls.__name__} doesn't implement get_communication_interface.")

    @classmethod
    def get_xml_arg_interface_name(cls) -> str:
        return f"{cls.get_communication_interface()}_name"

    @classmethod
    def from_xml_tree(cls: Type['RosDeclaration'], xml_tree: ET.Element) -> 'RosDeclaration':
        """Create an instance of the class from an XML tree."""
        assert_xml_tag_ok(cls, xml_tree)
        interface_name = read_value_from_xml_arg_or_child(
            cls, xml_tree, cls.get_xml_arg_interface_name(), (BtGetValueInputPort, str))
        interface_type = get_xml_argument(cls, xml_tree, "type")
        interface_alias = get_xml_argument(cls, xml_tree, "name", none_allowed=True)
        return cls(interface_name, interface_type, interface_alias)

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
                f"Error: SCXML {self.__class__.__name__}: " \
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
        raise RuntimeError(
            f"Error: SCXML {self.__class__.__name__} cannot be converted to plain SCXML.")

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), f"Error: SCXML {self.__class__.__name__}: invalid parameters."
        xml_declaration = ET.Element(self.get_tag_name(),
                                     {"name": self._interface_alias,
                                      self.get_xml_arg_interface_name(): self._interface_name,
                                      "type": self._interface_type})
        return xml_declaration


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

    @classmethod
    def get_callback_type(cls) -> CallbackType:
        """Return the callback type of a specific ROS Callback subclass"""
        raise NotImplementedError(f"{cls.__name__} doesn't implement get_callback_type.")

    @classmethod
    def from_xml_tree(cls: Type['RosCallback'], xml_tree: ET.Element) -> 'RosCallback':
        """Create an instance of the class from an XML tree."""
        assert_xml_tag_ok(cls, xml_tree)
        interface_name = get_xml_argument(cls, xml_tree, "name")
        target_state = get_xml_argument(cls, xml_tree, "target")
        condition = get_xml_argument(cls, xml_tree, "cond", none_allowed=True)
        exec_body = execution_body_from_xml(xml_tree, cls.get_callback_type())
        return cls(interface_name, target_state, condition, exec_body)

    def __init__(self, interface_decl: Union[str, RosDeclaration], target_state: str,
                 condition: Optional[str] = None, exec_body: Optional[ScxmlExecutionBody] = None
                 ) -> None:
        """
        Constructor of ROS callback.

        :param interface_decl: ROS interface declaration to be used in the callback, or its name.
        :param target_state: Name of the state to transition to after the callback.
        :param condition: Condition to be met for the callback to be executed.
        :param exec_body: Executable body of the callback.
        """
        if exec_body is None:
            exec_body: ScxmlExecutionBody = []
        self._interface_name: str = ""
        if isinstance(interface_decl, self.get_declaration_type()):
            self._interface_name = interface_decl.get_name()
        else:
            assert is_non_empty_string(self.__class__, "name", interface_decl)
            self._interface_name = interface_decl
        self._target: str = target_state
        self._condition: Optional[str] = condition
        self._body: ScxmlExecutionBody = exec_body
        assert self.check_validity(), \
            f"Error: SCXML {self.__class__.__name__}: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(self.__class__, "name", self._interface_name)
        valid_target = is_non_empty_string(self.__class__, "target", self._target)
        valid_condition = self._condition is None or \
            is_non_empty_string(self.__class__, "cond", self._condition)
        valid_body = self._body is None or valid_execution_body(self._body)
        if not valid_body:
            print(f"Error: SCXML {self.__class__.__name__}: invalid entries in executable body.")
        return valid_name and valid_target and valid_condition and valid_body

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ROS interface used in the callback exists."""
        raise NotImplementedError(
            f"{self.__class__.__name__} doesn't implement check_interface_defined.")

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        """Translate the ROS interface name to a plain scxml event."""
        raise NotImplementedError(
            f"{self.__class__.__name__} doesn't implement get_plain_scxml_event.")

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ROS entries in the callback are correctly defined."""
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            f"Error: SCXML {self.__class__.__name__}: invalid type of ROS declarations container."
        if not self.check_interface_defined(ros_declarations):
            print(f"Error: SCXML {self.__class__.__name__}: "
                  f"undefined ROS interface {self._interface_name}.")
            return False
        valid_body = super().check_valid_ros_instantiations(ros_declarations)
        if not valid_body:
            print(f"Error: SCXML {self.__class__.__name__}: "
                  f"body of {self._interface_name} has invalid ROS instantiations.")
        return valid_body

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlTransition:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            f"Error: SCXML {self.__class__.__name__}: invalid ROS instantiations."
        event_name = self.get_plain_scxml_event(ros_declarations)
        target = self._target
        condition = self._condition
        if condition is not None:
            condition = get_plain_expression(condition, self.get_callback_type())
        body = as_plain_execution_body(self._body, ros_declarations)
        return ScxmlTransition(target, [event_name], condition, body)

    def as_xml(self) -> ET.Element:
        """Convert the ROS callback to an XML element."""
        assert self.check_validity(), f"Error: SCXML {self.__class__.__name__}: invalid parameters."
        xml_callback = ET.Element(self.get_tag_name(),
                                  {"name": self._interface_name, "target": self._target})
        if self._condition is not None:
            xml_callback.set("cond", self._condition)
        for body_elem in self._body:
            xml_callback.append(body_elem.as_xml())
        return xml_callback


class RosTrigger(ScxmlSend):
    """Base class for ROS triggers in SCXML."""

    @classmethod
    def get_tag_name(cls) -> str:
        """XML tag name for the ROS trigger type."""
        raise NotImplementedError(f"{cls.__name__} doesn't implement get_tag_name.")

    @classmethod
    def get_declaration_type(cls) -> Type[RosDeclaration]:
        """
        Get the type of ROS declaration related to the trigger.

        Examples: RosServiceClient, RosActionClient, ...
        """
        raise NotImplementedError(f"{cls.__name__} doesn't implement get_declaration_type.")

    @staticmethod
    def get_additional_arguments() -> List[str]:
        """Get the names of additional arguments in the SCXML-ROS tag."""
        return []

    @classmethod
    def from_xml_tree(cls: Type['RosTrigger'],
                      xml_tree: ET.Element, cb_type: CallbackType) -> 'RosTrigger':
        """
        Create an instance of the class from an XML tree.

        :param xml_tree: XML tree to be used for the creation of the instance.
        :param additional_args: Additional arguments to be parsed from the SCXML-ROS tag.
        """
        assert_xml_tag_ok(cls, xml_tree)
        interface_name = get_xml_argument(cls, xml_tree, "name")
        additional_arg_values: Dict[str, str] = {}
        for arg_name in cls.get_additional_arguments():
            additional_arg_values[arg_name] = get_xml_argument(cls, xml_tree, arg_name)
        fields = [RosField.from_xml_tree(field) for field in xml_tree
                  if field.tag is not ET.Comment]
        return cls(interface_name, fields, cb_type, additional_arg_values)

    def __init__(self, interface_decl: Union[str, RosDeclaration],
                 fields: List[RosField],
                 cb_type: CallbackType,
                 additional_args: Optional[Dict[str, str]] = None) -> None:
        """
        Constructor of a generic ROS trigger.

        :param interface_decl: ROS interface declaration to be used in the trigger, or its name.
        :param fields: Name of fields that are sent together with the trigger.
        :param cb_type: Type of of callback executing this ROS trigger.
        :param additional_args: Additional arguments in the SCXML-ROS tag.
        """
        if additional_args is None:
            additional_args = {}
        self._interface_name: str = ""
        if isinstance(interface_decl, self.get_declaration_type()):
            self._interface_name = interface_decl.get_name()
        else:
            assert is_non_empty_string(self.__class__, "name", interface_decl)
            self._interface_name = interface_decl
        self._fields: List[RosField] = fields
        self._additional_args: Dict[str, str] = additional_args
        self._cb_type: CallbackType = cb_type
        assert self.check_validity(), f"Error: SCXML {self.__class__.__name__}: invalid parameters."

    def append_field(self, field: RosField) -> None:
        assert isinstance(field, RosField), "Error: SCXML topic publish: invalid field."
        self._fields.append(field)

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler):
        """Update the values of potential entries making use of BT ports."""
        for field in self._fields:
            field.update_bt_ports_values(bt_ports_handler)

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(self.__class__, "name", self._interface_name)
        valid_fields = all(isinstance(field, RosField) for field in self._fields)
        valid_additional_args = all(is_non_empty_string(self.__class__, arg_name, arg_value)
                                    for arg_name, arg_value in self._additional_args.items())
        if not valid_fields:
            print(f"Error: SCXML {self.__class__.__name__}: "
                  f"invalid entries in fields of {self._interface_name}.")
        if not valid_additional_args:
            print(f"Error: SCXML {self.__class__.__name__}: "
                  f"invalid entries in additional arguments of {self._interface_name}.")
        return valid_name and valid_fields

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ROS interface used in the trigger exists."""
        raise NotImplementedError(
            f"{self.__class__.__name__} doesn't implement check_interface_defined.")

    def check_fields_validity(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if all fields are assigned, given the ROS interface definition."""
        raise NotImplementedError(
            f"{self.__class__.__name__} doesn't implement check_fields_validity.")

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        """Translate the ROS interface name to a plain scxml event."""
        raise NotImplementedError(
            f"{self.__class__.__name__} doesn't implement get_plain_scxml_event.")

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ROS entries in the trigger are correctly defined."""
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            f"Error: SCXML {self.__class__.__name__}: invalid type of ROS declarations container."
        if not self.check_interface_defined(ros_declarations):
            print(f"Error: SCXML {self.__class__.__name__}: "
                  f"undefined ROS interface {self._interface_name}.")
            return False
        if not self.check_fields_validity(ros_declarations):
            print(f"Error: SCXML {self.__class__.__name__}: "
                  f"invalid fields for {self._interface_name}.")
            return False
        return True

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlSend:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            f"Error: SCXML {self.__class__.__name__}: invalid ROS instantiations."
        event_name = self.get_plain_scxml_event(ros_declarations)
        params = [field.as_plain_scxml(ros_declarations) for field in self._fields]
        plain_cb_type = CallbackType.get_plain_callback(self._cb_type)
        for param_name, param_value in self._additional_args.items():
            params.append(ScxmlParam(param_name, plain_cb_type, expr=param_value))
        return ScxmlSend(event_name, params, plain_cb_type)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), f"Error: SCXML {self.__class__.__name__}: invalid parameters."
        xml_trigger = ET.Element(self.get_tag_name(), {"name": self._interface_name})
        for arg_name, arg_value in self._additional_args.items():
            xml_trigger.set(arg_name, arg_value)
        for field in self._fields:
            xml_trigger.append(field.as_xml())
        return xml_trigger
