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
Generic class for generators of SCXML state machine for specific ROS communication interfaces.
"""

from typing import Dict, Iterator, List, Optional, Type

from as2fm.as2fm_common.array_type import get_default_expression_for_type
from as2fm.as2fm_common.common import value_to_string_expr
from as2fm.jani_generator.jani_entries import JaniModel
from as2fm.scxml_converter.data_types.type_utils import get_data_type_from_string
from as2fm.scxml_converter.scxml_entries import ScxmlData, ScxmlRoot
from as2fm.scxml_converter.scxml_entries.utils import ROS_FIELD_PREFIX


class RosCommunicationHandler:
    """
    Object storing the declarations related to a ROS interface and creating an handler for them.
    """

    @staticmethod
    def get_interface_prefix() -> str:
        """
        Get the prefix used for the interface.

        :return: The prefix used for the interface.
        """
        raise NotImplementedError("Method get_interface_prefix must be implemented.")

    def __init__(self):
        """Initialize the object completely empty."""
        # The name of the communication channel, shared across all automata
        self._interface_name: Optional[str] = None
        # The type of the communication channel
        self._interface_type: Optional[str] = None
        # The name of the automaton providing the server of the communication channel
        self._server_automaton: Optional[str] = None
        # The names of the automata providing the clients of the communication channel
        self._clients_automata: List[str] = []

    def _set_name_and_type(self, interface_name: str, interface_type: str) -> None:
        """Setter to add and verify the name and type of a new ROS declaration."""
        if self._interface_name is None:
            self._interface_name = interface_name
            self._interface_type = interface_type
        else:
            assert (
                self._interface_name == interface_name
            ), f"Error: Interface name {interface_name} does not match {self._interface_name}."
            assert self._interface_type == interface_type, (
                f"Error: Interface type {interface_type} does not match {self._interface_type} for "
                f"interface name {self._interface_name}."
            )

    def _assert_validity(self):
        """
        Make sure service_name and service_type are set and a server and at least one client exist.
        """
        assert self._interface_name is not None, "Interface name not set."
        assert self._interface_type is not None, "Interface type not set."
        assert (
            self._server_automaton is not None
        ), f"ROS server not provided for {self._interface_name}."
        assert (
            len(self._clients_automata) > 0
        ), f"No ROS clients provided for {self._interface_name}."

    def set_server(self, interface_name: str, interface_type: str, automaton_name: str) -> None:
        """
        Set the server of the ROS interface.
        There must be exactly one.

        :interface_name: The name of the ROS interface.
        :interface_type: The type of the ROS interface (e.g. std_srvs/SetBool).
        :automaton_name: The name of the JANI automaton that implements this server.
        """
        self._set_name_and_type(interface_name, interface_type)
        assert (
            self._server_automaton is None
        ), f"Found more than one server for interface {interface_name}."
        self._server_automaton = automaton_name

    def add_client(self, interface_name: str, interface_type: str, automaton_name: str) -> None:
        """
        Set the client of the service.
        There must be one or more.

        :interface_name: The name of the ROS interface.
        :interface_type: The type of the ROS interface (e.g. std_srvs/SetBool).
        :automaton_name: The name of the JANI automaton that implements this client.
        """
        self._set_name_and_type(interface_name, interface_type)
        assert (
            automaton_name not in self._clients_automata
        ), f"Service client for {automaton_name} already declared for service {interface_name}."
        self._clients_automata.append(automaton_name)

    def to_scxml(self) -> ScxmlRoot:
        """
        Generate the srv_handler automaton that implements the link between the server of this
        service and its clients.
        This ensures that only one request can be processed at the time and that the client receives
        only the response related to it's request.

        :return: Scxml object representing the necessary file content.
        """
        NotImplementedError("Method to_scxml must be implemented.")

    def _generate_datamodel_from_ros_fields(self, fields: Dict[str, str]) -> List[ScxmlData]:
        """
        Generate the ScxmlDataModel object from the ROS fields.

        :param fields: The field names and types of the ROS interface.
        :return: A list of ScxmlData object.
        """
        scxml_fields: List[ScxmlData] = []
        for field_name, field_type in fields.items():
            field_w_pref = ROS_FIELD_PREFIX + field_name
            field_py_type = get_data_type_from_string(field_type)
            default_expr = value_to_string_expr(get_default_expression_for_type(field_py_type))
            scxml_fields.append(ScxmlData(field_w_pref, default_expr, field_type))
        return scxml_fields


def update_ros_communication_handlers(
    automaton_name: str,
    handler_class: Type[RosCommunicationHandler],
    handlers_dict: Dict[str, RosCommunicationHandler],
    servers_dict: Dict[str, tuple],
    clients_dict: Dict[str, tuple],
):
    """
    Update the ROS communication handlers with the given clients and servers.

    :param automaton_name: The name of the automaton where the interfaces are declared.
    :param handlers_dict: The dictionary of ROS communication handlers to update.
    :param servers_dict: The dictionary of servers to add.
    :param clients_dict: The dictionary of clients to add.
    """
    assert issubclass(
        handler_class, RosCommunicationHandler
    ), f"The handler class {handler_class} must be a subclass of RosCommunicationHandler."
    for service_name, service_type in servers_dict.values():
        if service_name not in handlers_dict:
            handlers_dict[service_name] = handler_class()
        handlers_dict[service_name].set_server(service_name, service_type, automaton_name)
    for service_name, service_type in clients_dict.values():
        if service_name not in handlers_dict:
            handlers_dict[service_name] = handler_class()
        handlers_dict[service_name].add_client(service_name, service_type, automaton_name)


def generate_plain_scxml_from_handlers(
    handlers_dict: Dict[str, RosCommunicationHandler],
) -> Iterator[ScxmlRoot]:
    """
    Generate the plain SCXML models from the ROS communication handlers.

    :param handlers_dict: The dictionary of ROS communication handlers.
    :return: A generator of ScxmlRoot objects.
    """
    for handler in handlers_dict.values():
        yield handler.to_scxml()


def remove_empty_self_loops_from_interface_handlers_in_jani(jani_model: JaniModel) -> None:
    """
    Remove self-loops from srv_handler automata in the Jani model.

    :param jani_model: The Jani model to modify.
    """
    handlers_prefixes = [
        handler.get_interface_prefix() for handler in RosCommunicationHandler.__subclasses__()
    ]
    for automaton in jani_model.get_automata():
        # Modify the automaton in place
        for prefix in handlers_prefixes:
            if automaton.get_name().startswith(prefix):
                automaton.remove_empty_self_loop_edges()
                break
