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

"""Collection of SCXML utilities related to ROS functionalities."""

from typing import Dict, List, Optional, Tuple

from scxml_converter.scxml_entries.scxml_ros_field import RosField

from scxml_converter.scxml_entries.utils import all_non_empty_strings


MSG_TYPE_SUBSTITUTIONS = {
    "boolean": "bool",
}

BASIC_FIELD_TYPES = ['boolean',
                     'int8', 'int16', 'int32', 'int64',
                     'float', 'double']

"""Container for the ROS interface (e.g. topic or service) name and the related type"""
RosInterfaceAndType = Tuple[str, str]


def is_ros_type_known(type_definition: str, ros_interface: str) -> bool:
    """
    Check if python can import the provided type definition.

    :param type_definition: The type definition to check (e.g. std_msgs/Empty).
    """
    if not (isinstance(type_definition, str) and type_definition.count("/") == 1):
        return False
    interface_ns, interface_type = type_definition.split("/")
    if len(interface_ns) == 0 or len(interface_type) == 0:
        return False
    assert ros_interface in ["msg", "srv"], "Error: SCXML ROS declarations: unknown ROS interface."
    try:
        interface_importer = __import__(interface_ns + f'.{ros_interface}', fromlist=[''])
        _ = getattr(interface_importer, interface_type)
    except (ImportError, AttributeError):
        print(f"Error: SCXML ROS declarations: topic type {type_definition} not found.")
        return False
    return True


def is_msg_type_known(topic_definition: str) -> bool:
    """Check if python can import the provided topic definition."""
    return is_ros_type_known(topic_definition, "msg")


def is_srv_type_known(service_definition: str) -> bool:
    """Check if python can import the provided service definition."""
    return is_ros_type_known(service_definition, "srv")


def get_srv_type_params(service_definition: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Get the data fields of a service request and response type as pairs of name and type objects.
    """
    assert is_srv_type_known(service_definition), \
        f"Error: SCXML ROS declarations: service type {service_definition} not found."
    interface_ns, interface_type = service_definition.split("/")
    srv_module = __import__(interface_ns + '.srv', fromlist=[''])
    srv_class = getattr(srv_module, interface_type)

    # TODO: Fields can be nested. Look AS2FM/scxml_converter/src/scxml_converter/scxml_converter.py
    req = srv_class.Request.get_fields_and_field_types()
    for key in req.keys():
        # TODO: Support nested fields
        assert req[key] in BASIC_FIELD_TYPES, \
            f"Error: SCXML ROS declarations: service request type {req[key]} isn't a basic field."
        req[key] = MSG_TYPE_SUBSTITUTIONS.get(req[key], req[key])

    res = srv_class.Response.get_fields_and_field_types()
    for key in res.keys():
        assert res[key] in BASIC_FIELD_TYPES, \
            "Error: SCXML ROS declarations: service response type contains non-basic fields."
        res[key] = MSG_TYPE_SUBSTITUTIONS.get(res[key], res[key])

    return req, res


def replace_ros_interface_expression(msg_expr: str) -> str:
    """Convert a ROS interface expression (msg, req, res) to plain SCXML (event)."""
    scxml_prefix = "_event."
    # TODO: Use regex and ensure no other valid character exists before the initial underscore
    for ros_prefix in ["_msg.", "_req.", "_res."]:
        msg_expr = msg_expr.replace(ros_prefix, scxml_prefix)
    return msg_expr


def sanitize_ros_interface_name(interface_name: str) -> str:
    """Replace slashes in a ROS interface name."""
    assert isinstance(interface_name, str), \
        "Error: ROS interface sanitizer: interface name must be a string."
    # Remove potential prepended slash
    interface_name = interface_name.removeprefix("/")
    assert len(interface_name) > 0, \
        "Error: ROS interface sanitizer: interface name must not be empty."
    assert interface_name.count(" ") == 0, \
        "Error: ROS interface sanitizer: interface name must not contain spaces."
    return interface_name.replace("/", "__")


def generate_srv_request_event(service_name: str, automaton_name: str) -> str:
    """Generate the name of the event that triggers a service request."""
    return f"srv_{sanitize_ros_interface_name(service_name)}_req_client_{automaton_name}"


def generate_srv_response_event(service_name: str, automaton_name: str) -> str:
    """Generate the name of the event that provides the service response."""
    return f"srv_{sanitize_ros_interface_name(service_name)}_response_client_{automaton_name}"


def generate_srv_server_request_event(service_name: str) -> str:
    """Generate the name of the event that makes a service server start processing a request."""
    return f"srv_{sanitize_ros_interface_name(service_name)}_request"


def generate_srv_server_response_event(service_name: str) -> str:
    """Generate the name of the event that makes a service server send a response."""
    return f"srv_{sanitize_ros_interface_name(service_name)}_response"


class ScxmlRosDeclarationsContainer:
    """Object that contains a description of the ROS declarations in the SCXML root."""

    def __init__(self, automaton_name: str):
        """Constructor of container.

        :automaton_name: Name of the automaton these declarations belong to.
        """
        self._automaton_name: str = automaton_name
        # Dict of publishers and subscribers: topic name -> type
        self._publishers: Dict[str, RosInterfaceAndType] = {}
        self._subscribers: Dict[str, RosInterfaceAndType] = {}
        self._service_servers: Dict[str, RosInterfaceAndType] = {}
        self._service_clients: Dict[str, RosInterfaceAndType] = {}
        self._timers: Dict[str, float] = {}

    def get_automaton_name(self) -> str:
        """Get name of the automaton that these declarations are defined in."""
        return self._automaton_name

    def append_publisher(self, pub_name: str, topic_name: str, topic_type: str) -> None:
        assert all_non_empty_strings(pub_name, topic_name, topic_type), \
            "Error: ROS declarations: publisher name, topic name and type must be strings."
        assert pub_name not in self._publishers, \
            f"Error: ROS declarations: topic publisher {pub_name} already declared."
        self._publishers[pub_name] = (topic_name, topic_type)

    def append_subscriber(self, sub_name: str, topic_name: str, topic_type: str) -> None:
        assert all_non_empty_strings(sub_name, topic_name, topic_type), \
            "Error: ROS declarations: subscriber name, topic name and type must be strings."
        assert sub_name not in self._subscribers, \
            f"Error: ROS declarations: topic subscriber {sub_name} already declared."
        self._subscribers[sub_name] = (topic_name, topic_type)

    def append_service_client(self, client_name: str, service_name: str, service_type: str) -> None:
        assert all_non_empty_strings(client_name, service_name, service_type), \
            "Error: ROS declarations: client name, service name and type must be strings."
        assert client_name not in self._service_clients, \
            f"Error: ROS declarations: service client {client_name} already declared."
        self._service_clients[client_name] = (service_name, service_type)

    def append_service_server(self, server_name: str, service_name: str, service_type: str) -> None:
        assert all_non_empty_strings(server_name, service_name, service_type), \
            "Error: ROS declarations: server name, service name and type must be strings."
        assert server_name not in self._service_servers, \
            f"Error: ROS declarations: service server {server_name} already declared."
        self._service_servers[server_name] = (service_name, service_type)

    def append_timer(self, timer_name: str, timer_rate: float) -> None:
        assert isinstance(timer_name, str), "Error: ROS declarations: timer name must be a string."
        assert isinstance(timer_rate, float) and timer_rate > 0, \
            "Error: ROS declarations: timer rate must be a positive number."
        assert timer_name not in self._timers, \
            f"Error: ROS declarations: timer {timer_name} already declared."
        self._timers[timer_name] = timer_rate

    def is_publisher_defined(self, pub_name: str) -> bool:
        return pub_name in self._publishers

    def is_subscriber_defined(self, sub_name: str) -> bool:
        return sub_name in self._subscribers

    def is_timer_defined(self, timer_name: str) -> bool:
        return timer_name in self._timers

    def get_timers(self) -> Dict[str, float]:
        return self._timers

    def is_service_client_defined(self, client_name: str) -> bool:
        return client_name in self._service_clients

    def is_service_server_defined(self, server_name: str) -> bool:
        return server_name in self._service_servers

    def get_service_client_type(self, client_name: str) -> Optional[str]:
        client_definition = self._service_clients.get(client_name, None)
        if client_definition is None:
            return None
        return client_definition[1]

    def get_service_server_type(self, server_name: str) -> Optional[str]:
        server_definition = self._service_servers.get(server_name, None)
        if server_definition is None:
            return None
        return server_definition[1]

    def check_valid_srv_req_fields(self, client_name: str, ros_fields: List[RosField]) -> bool:
        """Check if the provided fields match the service request type."""
        req_type = self.get_service_client_type(client_name)
        if req_type is None:
            print(f"Error: SCXML ROS declarations: unknown service client {client_name}.")
            return False
        req_fields, _ = get_srv_type_params(req_type)
        for ros_field in ros_fields:
            if ros_field.get_name() not in req_fields:
                print("Error: SCXML ROS declarations: "
                      f"unknown field {ros_field.get_name()} in service request.")
                return False
            req_fields.pop(ros_field.get_name())
        if len(req_fields) > 0:
            print("Error: SCXML ROS declarations: missing fields in service request.")
            for req_field in req_fields.keys():
                print(f"\t-{req_field}.")
            return False
        return True

    def check_valid_srv_res_fields(self, server_name: str, ros_fields: List[RosField]) -> bool:
        """Check if the provided fields match the service response type."""
        res_type = self.get_service_server_type(server_name)
        if res_type is None:
            print(f"Error: SCXML ROS declarations: unknown service server {server_name}.")
            return False
        _, res_fields = get_srv_type_params(res_type)
        for ros_field in ros_fields:
            if ros_field.get_name() not in res_fields:
                print("Error: SCXML ROS declarations: "
                      f"unknown field {ros_field.get_name()} in service response.")
                return False
            res_fields.pop(ros_field.get_name())
        if len(res_fields) > 0:
            print("Error: SCXML ROS declarations: missing fields in service response.")
            for res_field in res_fields.keys():
                print(f"\t-{res_field}.")
            return False
        return True
