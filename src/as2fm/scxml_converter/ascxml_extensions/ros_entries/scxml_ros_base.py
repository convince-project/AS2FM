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

from abc import abstractmethod
from typing import Dict, List, Optional, Type, Union

from lxml import etree as ET
from lxml.etree import _Element as XmlElement
from typing_extensions import Self

from as2fm.as2fm_common.common import is_comment
from as2fm.as2fm_common.logging import get_error_msg
from as2fm.scxml_converter.ascxml_extensions import AscxmlConfiguration, AscxmlDeclaration
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import (
    RosField,
    ScxmlBase,
    ScxmlExecutionBody,
    ScxmlParam,
    ScxmlRosDeclarationsContainer,
    ScxmlSend,
    ScxmlTransition,
    ScxmlTransitionTarget,
)
from as2fm.scxml_converter.scxml_entries.scxml_executable_entry import (
    set_execution_body_callback_type,
)
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import (
    CallbackType,
    get_plain_expression,
    is_non_empty_string,
)
from as2fm.scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok,
    get_xml_attribute,
    read_value_from_xml_arg_or_child,
)


class RosDeclaration(AscxmlDeclaration):
    """Base class for ROS declarations in SCXML."""

    @classmethod
    @abstractmethod
    def get_tag_name(cls) -> str:
        """The xml tag related to the ROS declaration."""
        pass

    @classmethod
    @abstractmethod
    def get_communication_interface(cls) -> str:
        """
        Which communication interface is used by the ROS declaration.

        Expected values: "service", "action"
        """
        pass

    @classmethod
    def get_xml_arg_interface_name(cls) -> str:
        return f"{cls.get_communication_interface()}_name"

    @classmethod
    def from_xml_tree_impl(
        cls: Type[Self],
        xml_tree: XmlElement,
        custom_data_types: Dict[str, StructDefinition],
    ) -> Self:
        """Create an instance of the class from an XML tree."""
        assert_xml_tag_ok(cls, xml_tree)
        valid_interface_name_types = [str] + AscxmlConfiguration.__subclasses__()
        interface_name = read_value_from_xml_arg_or_child(
            cls,
            xml_tree,
            cls.get_xml_arg_interface_name(),
            custom_data_types,
            valid_interface_name_types,
        )
        interface_type = get_xml_attribute(cls, xml_tree, "type")
        interface_alias = get_xml_attribute(cls, xml_tree, "name", undefined_allowed=True)
        assert isinstance(interface_name, (str, AscxmlConfiguration))  # MyPy check
        assert interface_type is not None  # MyPy check
        return cls(interface_name, interface_type, interface_alias)

    def __init__(
        self,
        interface_name: Union[str, AscxmlConfiguration],
        interface_type: str,
        interface_alias: Optional[str] = None,
    ):
        """
        Constructor of ROS declaration.

        :param interface_name: Comm. interface used by the declared ROS interface.
        :param interface_type: ROS type used for communication.
        :param interface_alias: Alias for the defined interface, used for ref. by the the handlers
        """
        self._interface_name = interface_name
        self._interface_type = interface_type
        self._interface_alias = interface_alias
        assert isinstance(interface_name, (str, AscxmlConfiguration)), (
            f"Error: SCXML {self.get_tag_name()}: "
            f"invalid type of interface_name {type(interface_name)}."
        )
        if self._interface_alias is None:
            assert isinstance(interface_name, str) and len(interface_name) > 0, get_error_msg(
                self.get_xml_origin(), "An alias name is required for dynamic ROS interfaces."
            )
            self._interface_alias = interface_name

    def get_interface_name(self) -> str:
        """Get the name of the ROS comm. interface."""
        assert isinstance(self._interface_name, str), get_error_msg(
            self.get_xml_origin(), "Need to extract the interface name from config variables."
        )
        return self._interface_name

    def get_interface_type(self) -> str:
        """Get the ROS type used for communication."""
        return self._interface_type

    def get_name(self) -> str:
        """Get the alias name of the ROS interface."""
        assert isinstance(self._interface_alias, str)  # MyPy  check
        return self._interface_alias

    @abstractmethod
    def check_valid_interface_type(self) -> bool:
        pass

    def check_validity(self) -> bool:
        valid_alias = is_non_empty_string(type(self), "name", self._interface_alias)
        valid_action_name = isinstance(
            self._interface_name, AscxmlConfiguration
        ) or is_non_empty_string(type(self), "interface_name", self._interface_name)
        valid_action_type = self.check_valid_interface_type()
        return valid_alias and valid_action_name and valid_action_type

    def check_valid_instantiation(self) -> bool:
        """Check if the interface name is still undefined (i.e. from BT ports)."""
        return is_non_empty_string(type(self), "interface_name", self._interface_name)

    def preprocess_declaration(self, ascxml_declarations: List[AscxmlDeclaration]):
        if isinstance(self._interface_name, AscxmlConfiguration):
            self._interface_name.update_configured_value(ascxml_declarations)
            assert self._interface_name.is_constant_value(), get_error_msg(
                self.get_xml_origin(), "ROS declaration expect constant configurable values."
            )
            self._interface_name = self._interface_name.get_configured_value()

    def as_plain_scxml(self, struct_declarations, ascxml_declarations, **kwargs) -> List[ScxmlBase]:
        # This is discarded in the to_plain_scxml_and_declarations method from ScxmlRoot
        raise RuntimeError(
            f"Error: SCXML {self.__class__.__name__} cannot be converted to plain SCXML."
        )

    def is_plain_scxml(self):
        return False

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), f"Error: SCXML {self.__class__.__name__}: invalid parameters."
        xml_declaration = ET.Element(
            self.get_tag_name(),
            {
                "name": self._interface_alias,
                self.get_xml_arg_interface_name(): self._interface_name,
                "type": self._interface_type,
            },
        )
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
    def from_xml_tree_impl(
        cls: Type["RosCallback"],
        xml_tree: XmlElement,
        custom_data_types: Dict[str, StructDefinition],
    ) -> "RosCallback":
        """Create an instance of the class from an XML tree."""
        assert_xml_tag_ok(cls, xml_tree)
        interface_name = get_xml_attribute(cls, xml_tree, "name")
        condition = get_xml_attribute(cls, xml_tree, "cond", undefined_allowed=True)
        transition_targets = cls.load_transition_targets_from_xml(xml_tree, custom_data_types)
        return cls(interface_name, transition_targets, condition)

    @classmethod
    def get_interface_name(
        cls: Type["RosCallback"], interface_decl: Union[str, RosDeclaration]
    ) -> str:
        """
        Extract the interface name from either a string or a RosDeclaration.

        :param interface_decl: The interface declaration to extract the information from.
        :return: A string providing the unique ROS communication interface name.
        """
        if isinstance(interface_decl, cls.get_declaration_type()):
            return interface_decl.get_name()
        assert is_non_empty_string(cls, "name", interface_decl)
        return interface_decl

    @classmethod
    def make_single_target_transition(
        cls: Type["RosCallback"],
        interface_decl: Union[str, RosDeclaration],
        target: str,
        condition: Optional[str] = None,
        body: Optional[ScxmlExecutionBody] = None,
    ) -> "RosCallback":
        """
        Generate a RosCallback with exactly one target, like in vanilla SCXML.

        :param interface_decl: The ROS declaration this Callback refers to.
        :param target: The state to transition to once the callback is executed.
        :param condition: The condition that enables this callback.
        :param body: The operations to execute when running this callback.
        """
        targets = [ScxmlTransitionTarget(target, None, body)]
        return cls(interface_decl, targets, condition)

    def __init__(
        self,
        interface_decl: Union[str, RosDeclaration],
        targets: List[ScxmlTransitionTarget],
        condition: Optional[str] = None,
    ) -> None:
        """
        Constructor of ROS callback.

        :param interface_decl: ROS interface declaration to be used in the callback, or its name.
        :param targets: A list of targets reachable from this callback.
        :param condition: Condition to be met for the callback to be executed.
        """
        super().__init__(targets, condition=condition)
        self._interface_name = self.get_interface_name(interface_decl)
        assert self.check_validity(), f"Error: SCXML {self.get_tag_name()}: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(self.__class__, "name", self._interface_name)
        valid_targets = len(self._targets) > 0 and all(
            target.check_validity() for target in self._targets
        )
        valid_condition = self._condition is None or is_non_empty_string(
            self.__class__, "cond", self._condition
        )
        if not valid_targets:
            print(f"Error: SCXML {self.get_tag_name()}: invalid target entries.")
        if valid_targets and len(self._targets) > 1 and self._condition is not None:
            print(
                "Error: SCXML {self.get_tag_name()}: No support for conditional callbacks "
                "with multiple targets."
            )
            valid_targets = False
        return valid_name and valid_targets and valid_condition

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ROS interface used in the callback exists."""
        raise NotImplementedError(
            f"{self.get_tag_name()} doesn't implement check_interface_defined."
        )

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        """Translate the ROS interface name to a plain scxml event."""
        raise NotImplementedError(f"{self.get_tag_name()} doesn't implement get_plain_scxml_event.")

    def check_valid_ros_instantiations(
        self, ros_declarations: ScxmlRosDeclarationsContainer
    ) -> bool:
        """Check if the ROS entries in the callback are correctly defined."""
        assert isinstance(
            ros_declarations, ScxmlRosDeclarationsContainer
        ), f"Error: SCXML {self.get_tag_name()}: invalid type of ROS declarations container."
        if not self.check_interface_defined(ros_declarations):
            print(
                f"Error: SCXML {self.get_tag_name()}: "
                f"undefined ROS interface {self._interface_name}."
            )
            return False
        valid_body = super().check_valid_ros_instantiations(ros_declarations)
        if not valid_body:
            print(
                f"Error: SCXML {self.get_tag_name()}: "
                f"body of {self._interface_name} has invalid ROS instantiations."
            )
        return valid_body

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ros_declarations: ScxmlRosDeclarationsContainer,
    ) -> List[ScxmlTransition]:
        assert self.check_valid_ros_instantiations(
            ros_declarations
        ), f"Error: SCXML {self.get_tag_name()}: invalid ROS instantiations."
        new_targets: List[ScxmlTransitionTarget] = []
        for target in self._targets:
            target.set_callback_type(self.get_callback_type())
            new_targets.extend(target.as_plain_scxml(struct_declarations, ros_declarations))
            if new_targets[-1]._body is not None:
                set_execution_body_callback_type(new_targets[-1]._body, self.get_callback_type())
        event_name = self.get_plain_scxml_event(ros_declarations)
        condition = self._condition
        if condition is not None:
            condition = get_plain_expression(
                condition, self.get_callback_type(), struct_declarations
            )
        return [ScxmlTransition(new_targets, [event_name], condition)]

    def as_xml(self) -> XmlElement:
        """Convert the ROS callback to an XML element."""
        assert self.check_validity(), f"Error: SCXML {self.get_tag_name()}: invalid parameters."
        xml_element = super().as_xml()
        if len(self._events) > 0:
            _ = xml_element.attrib.pop("event")
        xml_element.set("name", self._interface_name)
        return xml_element


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
    def from_xml_tree_impl(
        cls: Type["RosTrigger"],
        xml_tree: XmlElement,
        custom_data_types: Dict[str, StructDefinition],
    ) -> "RosTrigger":
        """
        Create an instance of the class from an XML tree.

        :param xml_tree: XML tree to be used for the creation of the instance.
        :param additional_args: Additional arguments to be parsed from the SCXML-ROS tag.
        """
        assert_xml_tag_ok(cls, xml_tree)
        interface_name = get_xml_attribute(cls, xml_tree, "name")
        additional_arg_values: Dict[str, str] = {}
        for arg_name in cls.get_additional_arguments():
            additional_arg_values[arg_name] = get_xml_attribute(cls, xml_tree, arg_name)
        fields = [
            RosField.from_xml_tree(field, custom_data_types)
            for field in xml_tree
            if not is_comment(field)
        ]
        return cls(interface_name, fields, additional_arg_values)

    def __init__(
        self,
        interface_decl: Union[str, RosDeclaration],
        fields: List[RosField],
        additional_args: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Constructor of a generic ROS trigger.

        :param interface_decl: ROS interface declaration to be used in the trigger, or its name.
        :param fields: Name of fields that are sent together with the trigger.
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
        self._cb_type: Optional[CallbackType] = None
        assert self.check_validity(), f"Error: SCXML {self.__class__.__name__}: invalid parameters."

    def set_callback_type(self, cb_type: CallbackType):
        """Set the callback executing this trigger for this instance and its children."""
        self._cb_type = cb_type
        for field in self._fields:
            field.set_callback_type(cb_type)

    def append_field(self, field: RosField) -> None:
        assert isinstance(field, RosField), "Error: SCXML topic publish: invalid field."
        field.set_callback_type(self._cb_type)
        self._fields.append(field)

    def has_bt_blackboard_input(self, bt_ports_handler: BtPortsHandler):
        """Check whether the If entry reads content from the BT Blackboard."""
        for field in self._fields:
            if field.has_bt_blackboard_input(bt_ports_handler):
                return True
        return False

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler):
        """Update the values of potential entries making use of BT ports."""
        for field in self._fields:
            field.update_bt_ports_values(bt_ports_handler)

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(self.__class__, "name", self._interface_name)
        valid_fields = all(isinstance(field, RosField) for field in self._fields)
        valid_additional_args = all(
            is_non_empty_string(self.__class__, arg_name, arg_value)
            for arg_name, arg_value in self._additional_args.items()
        )
        if not valid_fields:
            print(
                f"Error: SCXML {self.__class__.__name__}: "
                f"invalid entries in fields of {self._interface_name}."
            )
        if not valid_additional_args:
            print(
                f"Error: SCXML {self.__class__.__name__}: "
                f"invalid entries in additional arguments of {self._interface_name}."
            )
        return valid_name and valid_fields

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ROS interface used in the trigger exists."""
        raise NotImplementedError(
            f"{self.__class__.__name__} doesn't implement check_interface_defined."
        )

    def check_fields_validity(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if all fields are assigned, given the ROS interface definition."""
        raise NotImplementedError(
            f"{self.__class__.__name__} doesn't implement check_fields_validity."
        )

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        """Translate the ROS interface name to a plain scxml event."""
        raise NotImplementedError(
            f"{self.__class__.__name__} doesn't implement get_plain_scxml_event."
        )

    def check_valid_ros_instantiations(
        self, ros_declarations: ScxmlRosDeclarationsContainer
    ) -> bool:
        """Check if the ROS entries in the trigger are correctly defined."""
        assert isinstance(
            ros_declarations, ScxmlRosDeclarationsContainer
        ), f"Error: SCXML {self.__class__.__name__}: invalid type of ROS declarations container."
        if not self.check_interface_defined(ros_declarations):
            print(
                f"Error: SCXML {self.__class__.__name__}: "
                f"undefined ROS interface {self._interface_name}."
            )
            return False
        if not self.check_fields_validity(ros_declarations):
            print(
                f"Error: SCXML {self.__class__.__name__}: "
                f"invalid fields for {self._interface_name}."
            )
            return False
        return True

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ros_declarations: ScxmlRosDeclarationsContainer,
    ) -> List[ScxmlSend]:
        assert self.check_valid_ros_instantiations(
            ros_declarations
        ), f"Error: SCXML {self.__class__.__name__}: invalid ROS instantiations."
        assert (
            self._cb_type is not None
        ), f"Error: SCXML {self.__class__.__name__}: {self._interface_name} has no callback type."
        event_name = self.get_plain_scxml_event(ros_declarations)
        plain_params = []
        for single_field in self._fields:
            plain_params.extend(single_field.as_plain_scxml(struct_declarations, ros_declarations))
        for param_name, param_value in self._additional_args.items():
            expanded_value = get_plain_expression(param_value, self._cb_type, struct_declarations)
            plain_params.append(ScxmlParam(param_name, expr=expanded_value))
        return [ScxmlSend(event_name, plain_params)]

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), f"Error: SCXML {self.__class__.__name__}: invalid parameters."
        xml_trigger = ET.Element(self.get_tag_name(), {"name": self._interface_name})
        for arg_name, arg_value in self._additional_args.items():
            xml_trigger.set(arg_name, arg_value)
        for field in self._fields:
            xml_trigger.append(field.as_xml())
        return xml_trigger
