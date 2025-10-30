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
from as2fm.as2fm_common.logging import get_error_msg, log_error, log_warning
from as2fm.scxml_converter.ascxml_extensions import AscxmlConfiguration, AscxmlDeclaration
from as2fm.scxml_converter.ascxml_extensions.ros_entries import RosField
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import (
    ScxmlBase,
    ScxmlExecutionBody,
    ScxmlParam,
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

    def set_node_name(self, node_name: str):
        """Setter for the node name related to the ROS declaration."""
        self._node_name = node_name

    def get_node_name(self) -> str:
        """Getter for the node name related to the ROS declaration."""
        return self._node_name

    @abstractmethod
    def check_valid_interface_type(self) -> bool:
        """Ensure the type of the declared interface is a valid ROS type."""
        pass

    def check_validity(self) -> bool:
        valid_alias = is_non_empty_string(type(self), "name", self._interface_alias)
        valid_action_name = isinstance(
            self._interface_name, AscxmlConfiguration
        ) or is_non_empty_string(type(self), "interface_name", self._interface_name)
        valid_interface_type = self.check_valid_interface_type()
        return valid_alias and valid_action_name and valid_interface_type

    def check_valid_instantiation(self) -> bool:
        """Check if the interface name is still undefined (i.e. from BT ports)."""
        return is_non_empty_string(type(self), "interface_name", self._interface_name)

    def preprocess_declaration(self, ascxml_declarations: List[AscxmlDeclaration], **kwargs):
        assert "model_name" in kwargs, get_error_msg(
            self.get_xml_origin(), "'model_name' not defined when processing a ROS declaration."
        )
        self.set_node_name(kwargs["model_name"])
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

    def is_plain_scxml(self, verbose: bool = False):
        if verbose:
            log_warning(None, f"No plain SCXML: {type(self)} is never plain.")
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
    @abstractmethod
    def get_tag_name(cls) -> str:
        """XML tag name for the ROS callback type."""
        pass

    @classmethod
    @abstractmethod
    def get_declaration_type(cls) -> Type[RosDeclaration]:
        """
        Get the type of ROS declaration related to the callback.

        Examples: RosSubscriber, RosPublisher, ...
        """
        pass

    @classmethod
    @abstractmethod
    def get_callback_type(cls) -> CallbackType:
        """Return the callback type of a specific ROS Callback subclass"""
        pass

    @abstractmethod
    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        """Translate the ROS interface name to a plain scxml event."""
        pass

    @classmethod
    def from_xml_tree_impl(
        cls: Type[Self],
        xml_tree: XmlElement,
        custom_data_types: Dict[str, StructDefinition],
    ) -> Self:
        """Create an instance of the class from an XML tree."""
        assert_xml_tag_ok(cls, xml_tree)
        interface_name = get_xml_attribute(cls, xml_tree, "name")
        assert interface_name is not None  # MyPy check
        condition = get_xml_attribute(cls, xml_tree, "cond", undefined_allowed=True)
        transition_targets = cls.load_transition_targets_from_xml(xml_tree, custom_data_types)
        return cls(interface_name, transition_targets, condition)

    @classmethod
    def get_interface_name(cls: Type[Self], interface_decl: Union[str, RosDeclaration]) -> str:
        """
        Extract the interface name from either a string or a RosDeclaration.

        :param interface_decl: The interface declaration to extract the information from.
        :return: A string providing the alias for the communication interface within the model.
        """
        if isinstance(interface_decl, RosDeclaration):
            assert isinstance(interface_decl, cls.get_declaration_type()), get_error_msg(
                interface_decl.get_xml_origin(),
                "Found mismatch between declaration and related callback.",
            )
            return interface_decl.get_name()
        assert is_non_empty_string(cls, "name", interface_decl)
        return interface_decl

    @classmethod
    def make_single_target_transition(  # type: ignore[override]
        cls: Type[Self],
        interface_decl: Union[str, RosDeclaration],
        target: str,
        condition: Optional[str] = None,
        body: Optional[ScxmlExecutionBody] = None,
    ) -> Self:
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

    def get_related_interface(
        self, ascxml_declarations: List[AscxmlDeclaration]
    ) -> Optional[RosDeclaration]:
        """Find the declared interface related to this callback."""
        for ascxml_decl in ascxml_declarations:
            if (
                isinstance(ascxml_decl, RosDeclaration)
                and ascxml_decl.get_name() == self._interface_name
            ):
                assert isinstance(ascxml_decl, self.get_declaration_type()), get_error_msg(
                    self.get_xml_origin(),
                    f"The interface {self._interface_name} defined type and the one "
                    "required by the callback are not matching.",
                )
                return ascxml_decl
        return None

    def check_interface_defined(self, ascxml_declarations: List[AscxmlDeclaration]) -> bool:
        """Check if the ROS interface used in the callback exists."""
        related_decl = self.get_related_interface(ascxml_declarations)
        return related_decl is not None

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> List[ScxmlBase]:
        related_declaration = self.get_related_interface(ascxml_declarations)
        assert related_declaration is not None, get_error_msg(
            self.get_xml_origin(), "Cannot find related ROS declaration."
        )
        new_targets: List[ScxmlTransitionTarget] = []
        for target in self._targets:
            target.set_callback_type(self.get_callback_type())
            new_targets.extend(
                target.as_plain_scxml(struct_declarations, ascxml_declarations, **kwargs)
            )
            if new_targets[-1]._body is not None:
                set_execution_body_callback_type(new_targets[-1]._body, self.get_callback_type())
        event_name = self.get_plain_scxml_event(related_declaration)
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
    @abstractmethod
    def get_tag_name(cls) -> str:
        """XML tag name for the ROS trigger type."""
        pass

    @classmethod
    @abstractmethod
    def get_declaration_type(cls) -> Type[RosDeclaration]:
        """
        Get the type of ROS declaration related to the trigger.

        Examples: RosServiceClient, RosActionClient, ...
        """
        pass

    @abstractmethod
    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        """Translate the ROS interface name to a plain scxml event."""
        pass

    @abstractmethod
    def check_fields_validity(self, ascxml_declaration: AscxmlDeclaration) -> bool:
        """Check if all the fields defined in the declared ROS interface are assigned."""
        pass

    @staticmethod
    def get_additional_arguments() -> List[str]:
        """Get the names of additional arguments in the SCXML-ROS tag."""
        return []

    @classmethod
    def from_xml_tree_impl(
        cls: Type[Self],
        xml_tree: XmlElement,
        custom_data_types: Dict[str, StructDefinition],
    ) -> Self:
        """
        Create an instance of the class from an XML tree.

        :param xml_tree: XML tree to be used for the creation of the instance.
        :param additional_args: Additional arguments to be parsed from the SCXML-ROS tag.
        """
        assert_xml_tag_ok(cls, xml_tree)
        interface_name = get_xml_attribute(cls, xml_tree, "name")
        assert interface_name is not None  # MyPy check
        additional_arg_values: Dict[str, str] = {}
        for arg_name in cls.get_additional_arguments():
            extra_arg = get_xml_attribute(cls, xml_tree, arg_name)
            assert extra_arg is not None  # MyPy check
            additional_arg_values[arg_name] = extra_arg
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
        if isinstance(interface_decl, RosDeclaration):
            assert isinstance(interface_decl, self.get_declaration_type()), get_error_msg(
                self.get_xml_origin(), "Mismatch between the declared and expected interface type."
            )
            self._interface_name = interface_decl.get_name()
        else:
            assert is_non_empty_string(self.__class__, "name", interface_decl)
            self._interface_name = interface_decl
        self._params: List[RosField] = fields  # type: ignore
        self._additional_args: Dict[str, str] = additional_args
        self._cb_type: Optional[CallbackType] = None
        assert self.check_validity(), f"Error: SCXML {self.__class__.__name__}: invalid parameters."

    def set_callback_type(self, cb_type: CallbackType):
        """Set the callback executing this trigger for this instance and its children."""
        self._cb_type = cb_type
        for field in self._params:
            field.set_callback_type(cb_type)

    def append_field(self, field: RosField) -> None:
        assert isinstance(field, RosField), get_error_msg(self.get_xml_origin(), "Invalid field.")
        super().append_param(field)

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(type(self), "name", self._interface_name)
        valid_fields = all(isinstance(field, RosField) for field in self._params)
        valid_additional_args = all(
            is_non_empty_string(self.__class__, arg_name, arg_value)
            for arg_name, arg_value in self._additional_args.items()
        )
        if not valid_fields:
            log_error(self.get_xml_origin(), "Some of the fields have unexpected type.")
        if not valid_additional_args:
            log_error(self.get_xml_origin(), "Found invalid additional arguments.")
        return valid_name and valid_fields and valid_additional_args

    def get_related_interface(
        self, ascxml_declarations: List[AscxmlDeclaration]
    ) -> Optional[RosDeclaration]:
        """Find the declared interface related to this callback."""
        for ascxml_decl in ascxml_declarations:
            if (
                isinstance(ascxml_decl, RosDeclaration)
                and ascxml_decl.get_name() == self._interface_name
            ):
                assert isinstance(ascxml_decl, self.get_declaration_type()), get_error_msg(
                    self.get_xml_origin(),
                    f"The interface {self._interface_name} defined type and the one "
                    "required by the callback are not matching.",
                )
                return ascxml_decl
        return None

    def check_interface_defined(self, ascxml_declarations: List[AscxmlDeclaration]) -> bool:
        """Check if the ROS interface used in the callback exists."""
        related_decl = self.get_related_interface(ascxml_declarations)
        return related_decl is not None

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> List[ScxmlBase]:
        related_ros_decl = self.get_related_interface(ascxml_declarations)
        assert related_ros_decl is not None, get_error_msg(
            self.get_xml_origin(), "Cannot find related ROS declaration."
        )
        assert self.check_fields_validity(related_ros_decl), get_error_msg(
            self.xml_origin(), "Found invalid fields, w.r.t. the declared type."
        )
        assert self._cb_type is not None, get_error_msg(
            self.get_xml_origin(), "No callback type defined."
        )
        event_name = self.get_plain_scxml_event(related_ros_decl)
        plain_params: List[ScxmlParam] = []
        for single_field in self._params:
            for param in single_field.as_plain_scxml(
                struct_declarations, ascxml_declarations, **kwargs
            ):
                assert isinstance(param, ScxmlParam)  # MyPy check
                plain_params.append(param)
        for param_name, param_value in self._additional_args.items():
            expanded_value = get_plain_expression(param_value, self._cb_type, struct_declarations)
            plain_params.append(ScxmlParam(param_name, expr=expanded_value))
        return [ScxmlSend(event_name, plain_params)]

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), get_error_msg(self.get_xml_origin(), "Invalid parameters.")
        xml_trigger = ET.Element(self.get_tag_name(), {"name": self._interface_name})
        for arg_name, arg_value in self._additional_args.items():
            xml_trigger.set(arg_name, arg_value)
        for field in self._params:
            xml_trigger.append(field.as_xml())
        return xml_trigger
