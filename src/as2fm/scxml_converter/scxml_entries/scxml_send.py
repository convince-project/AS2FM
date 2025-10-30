# Copyright (c) 2025 - for information on the respective copyright owner
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

from copy import deepcopy
from typing import Dict, List, Optional, Tuple

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.common import is_comment
from as2fm.as2fm_common.logging import get_error_msg, log_warning
from as2fm.scxml_converter.ascxml_extensions import AscxmlConfiguration, AscxmlDeclaration
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import (
    ScxmlBase,
    ScxmlParam,
)
from as2fm.scxml_converter.scxml_entries.scxml_executable_entry import (
    EventsToAutomata,
    ScxmlExecutableEntry,
)
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import (
    CallbackType,
    convert_expression_with_string_literals,
)


class ScxmlSend(ScxmlExecutableEntry):
    """This class represents a send action."""

    @staticmethod
    def get_tag_name() -> str:
        return "send"

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, custom_data_types: Dict[str, StructDefinition]
    ) -> "ScxmlSend":
        """
        Create a ScxmlSend object from an XML tree.

        :param xml_tree: The XML tree to create the object from.
        :param cb_type: The kind of callback executing this SCXML entry.
        """
        assert (
            xml_tree.tag == ScxmlSend.get_tag_name()
        ), f"Error: SCXML send: XML tag name is not {ScxmlSend.get_tag_name()}."
        event = xml_tree.attrib["event"]
        target = xml_tree.attrib.get("target")
        params: List[ScxmlParam] = []
        assert params is not None, "Error: SCXML send: params is not valid."
        for param_xml in xml_tree:
            if is_comment(param_xml):
                continue
            params.append(ScxmlParam.from_xml_tree(param_xml, custom_data_types))
        return ScxmlSend(event, params, target)

    def __init__(
        self,
        event: str,
        params: Optional[List[ScxmlParam]] = None,
        target_automaton: Optional[str] = None,
        delay: Optional[int] = None,
    ):
        """
        Construct a new ScxmlSend object.

        :param event: The name of the event sent when executing this entry.
        :param params: The parameters to send as part of the event.
        :param target_automaton: The target automaton for this send event.
        """
        if params is None:
            params = []
        self._event = event
        self._params = params
        self._target_automaton = target_automaton
        self._delay = delay
        self._cb_type: Optional[CallbackType] = None

    def set_callback_type(self, cb_type: CallbackType) -> None:
        """Set the cb type for this entry and its children."""
        self._cb_type = cb_type

    def update_configurable_entry(self, ascxml_declarations: List[AscxmlDeclaration]):
        for param in self._params:
            param.update_configured_value(ascxml_declarations)

    def get_config_request_receive_events(self) -> Optional[Tuple[str, str]]:
        """
        Return the events for requesting-receiving the updated value of a conf. entry, if any."""
        req_rec_events: Optional[Tuple[str, str]] = None
        for param in self._params:
            param_expr = param.get_expr()
            if isinstance(param_expr, AscxmlConfiguration):
                param_events = param_expr.get_config_request_response_events()
                if req_rec_events is None:
                    req_rec_events = param_events
                elif param_events is not None:
                    assert req_rec_events == param_events, get_error_msg(
                        self.get_xml_origin(), "Only one kind of configurable variables expected."
                    )
        return req_rec_events

    def get_event(self) -> str:
        """Get the event to send."""
        return self._event

    def get_params(self) -> List[ScxmlParam]:
        """Get the parameters to send."""
        return self._params

    def get_target_automaton(self) -> Optional[str]:
        """Get the target automata associated to this send event."""
        return self._target_automaton

    def set_target_automaton(self, target_automaton: str) -> None:
        """Set the target automata associated to this send event."""
        self._target_automaton = target_automaton

    def check_validity(self) -> bool:
        valid_event = isinstance(self._event, str) and len(self._event) > 0
        valid_params = True
        for param in self._params:
            valid_param = isinstance(param, ScxmlParam) and param.check_validity()
            valid_params = valid_params and valid_param
        if not valid_event:
            print("Error: SCXML send: event is not valid.")
        if not valid_params:
            print(f"Error: SCXML send: one or more param invalid entries of event '{self._event}'.")
        return valid_event and valid_params

    def check_valid_ros_instantiations(self, _) -> bool:
        """Check if the ros instantiations have been declared."""
        # This has nothing to do with ROS. Return always True
        return True

    def append_param(self, param: ScxmlParam) -> None:
        assert (
            self.__class__ is ScxmlSend
        ), f"Error: SCXML send: cannot append param to derived class {self.__class__.__name__}."
        assert isinstance(param, ScxmlParam), get_error_msg(self.get_xml_origin(), "Invalid param.")
        param.set_callback_type(self._cb_type)
        self._params.append(param)

    def is_plain_scxml(self, verbose: bool = False) -> bool:
        if type(self) is ScxmlSend:
            all_plain_params = all(isinstance(param.get_expr(), str) for param in self._params)
            if not all_plain_params and verbose:
                log_warning(None, "No plain SCXML send: non-plain params found.")
            return all_plain_params
        if verbose:
            log_warning(None, f"No plain SCXML: tag {self.get_tag_name()} isn't a plain send.")
        return False

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> List[ScxmlBase]:
        # For now we don't need to do anything here. Change this to handle ros expr in scxml params.
        assert self._cb_type is not None, "Error: SCXML send: callback type not set."
        expanded_params: List[ScxmlParam] = []
        for param in self._params:
            param.set_callback_type(self._cb_type)
            expanded_params.extend(
                param.as_plain_scxml(struct_declarations, ascxml_declarations, **kwargs)
            )
        return [ScxmlSend(self._event, expanded_params, delay=self._delay)]

    def replace_strings_types_with_integer_arrays(self) -> "ScxmlSend":
        """Replace all string literals in the contained expressions."""
        new_params: List[ScxmlParam] = []
        for param in self._params:
            param_expr = param.get_expr()
            assert isinstance(param_expr, str)  # MyPy check
            new_param_expr = convert_expression_with_string_literals(param_expr)
            new_params.append(
                ScxmlParam(param.get_name(), expr=new_param_expr, cb_type=param._cb_type)
            )
        return ScxmlSend(self._event, new_params, self._target_automaton)

    def add_events_targets(self, events_to_models: EventsToAutomata):
        new_sends: List[ScxmlExecutableEntry] = []
        target_automata = events_to_models.get(self.get_event(), {"NONE"})
        assert self.get_target_automaton() is None, get_error_msg(
            self.get_xml_origin(), f"Target automaton already set for event {self.get_event()}."
        )
        for model in target_automata:
            new_entry = deepcopy(self)
            new_entry.set_target_automaton(model)
            new_sends.append(new_entry)
        return new_sends

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), "SCXML: found invalid send object."
        xml_send = ET.Element(ScxmlSend.get_tag_name(), {"event": self._event})
        if self._target_automaton is not None:
            xml_send.set("target", self._target_automaton)
        if self._delay is not None:
            # delay needs explicit conversion to str
            xml_send.set("delay", str(self._delay))
        for param in self._params:
            xml_send.append(param.as_xml())
        return xml_send
