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

from typing import Any, Dict, List, Tuple, Type

from scxml_converter.scxml_entries.scxml_ros_field import RosField

from scxml_converter.scxml_entries.utils import all_non_empty_strings


MSG_TYPE_SUBSTITUTIONS = {
    "boolean": "bool",
}

BASIC_FIELD_TYPES = ['boolean',
                     'int8', 'int16', 'int32', 'int64',
                     'float', 'double']

"""List of prefixes for ROS-related event data in SCXML."""
ROS_EVENT_PREFIXES = [
    "_msg.",                            # Topic-related
    "_req.", "_res.",                   # Service-related
    "_goal.", "_feedback.", "_result."  # Action-related
]


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


def is_action_type_known(action_definition: str) -> bool:
    """Check if python can import the provided action definition."""
    return is_ros_type_known(action_definition, "action")


def extract_params_from_ros_type(ros_interface_type: Type[Any]) -> Dict[str, str]:
    """
    Extract the data fields of a ROS message type as pairs of name and type objects.
    """
    fields = ros_interface_type.get_fields_and_field_types()
    for key in fields.keys():
        assert fields[key] in BASIC_FIELD_TYPES, \
            f"Error: SCXML ROS declarations: {ros_interface_type} {key} field is " \
            f"of type {fields[key]}, that is not supported."
        fields[key] = MSG_TYPE_SUBSTITUTIONS.get(fields[key], fields[key])
    return fields


def check_all_fields_known(ros_fields: List[RosField], field_types: Dict[str, str]) -> bool:
    """
    Check that all fields from ros_fields are in field_types, and that no field is missing.
    """
    for ros_field in ros_fields:
        if ros_field.get_name() not in field_types:
            print(f"Error: SCXML ROS declarations: unknown field {ros_field.get_name()}.")
            return False
        field_types.pop(ros_field.get_name())
    if len(field_types) > 0:
        print("Error: SCXML ROS declarations: there are missing fields:")
        for field_key in field_types.keys():
            print(f"\t-{field_key}.")
        return False
    return True


def get_srv_type_params(service_definition: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Get the fields of a service request and response as pairs of name and type objects.
    """
    assert is_srv_type_known(service_definition), \
        f"Error: SCXML ROS declarations: service type {service_definition} not found."
    interface_ns, interface_type = service_definition.split("/")
    srv_module = __import__(interface_ns + '.srv', fromlist=[''])
    srv_class = getattr(srv_module, interface_type)

    # TODO: Fields can be nested. Look AS2FM/scxml_converter/src/scxml_converter/scxml_converter.py
    req_fields = extract_params_from_ros_type(srv_class.Request)
    res_fields = extract_params_from_ros_type(srv_class.Response)

    return req_fields, res_fields


def get_action_type_params(action_definition: str
                           ) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """
    Get the fields of an action goal, feedback and result as pairs of name and type objects.
    """
    assert is_action_type_known(action_definition), \
        f"Error: SCXML ROS declarations: action type {action_definition} not found."
    interface_ns, interface_type = action_definition.split("/")
    action_module = __import__(interface_ns + '.action', fromlist=[''])
    action_class = getattr(action_module, interface_type)
    action_goal_fields = extract_params_from_ros_type(action_class.Goal)
    action_feedback_fields = extract_params_from_ros_type(action_class.Feedback)
    action_result_fields = extract_params_from_ros_type(action_class.Result)
    return action_goal_fields, action_feedback_fields, action_result_fields


def replace_ros_interface_expression(msg_expr: str) -> str:
    """Convert all ROS interface expressions (in ROS_EVENT_PREFIXES) to plain SCXML events."""
    scxml_prefix = "_event."
    # TODO: Use regex and ensure no other valid character exists before the initial underscore
    for ros_prefix in ROS_EVENT_PREFIXES:
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


def generate_action_goal_event(action_name: str, automaton_name: str) -> str:
    """Generate the name of the event that sends an action goal from a client to the server."""
    return f"action_{sanitize_ros_interface_name(action_name)}_goal_client_{automaton_name}"


def generate_action_goal_handle_event(action_name: str) -> str:
    """Generate the name of the event that triggers an action goal handling in the server."""
    return f"action_{sanitize_ros_interface_name(action_name)}_goal_handle"


def generate_action_feedback_event(action_name: str) -> str:
    """Generate the name of the event that sends a feedback from the action server."""
    return f"action_{sanitize_ros_interface_name(action_name)}_feedback"


def generate_action_feedback_handle_event(action_name: str, automaton_name: str) -> str:
    """Generate the name of the event that handles a feedback in an action client."""
    return f"action_{sanitize_ros_interface_name(action_name)}_" \
           f"feedback_handle_client_{automaton_name}"


def generate_action_result_event(action_name: str) -> str:
    """Generate the name of the event that sends a result from the action server."""
    return f"action_{sanitize_ros_interface_name(action_name)}_result"


def generate_action_result_handle_event(action_name: str, automaton_name: str) -> str:
    """Generate the name of the event that handles a result in an action client."""
    return f"action_{sanitize_ros_interface_name(action_name)}_" \
           f"result_handle_client_{automaton_name}"


class ScxmlRosDeclarationsContainer:
    """Object that contains a description of the ROS declarations in the SCXML root."""

    def __init__(self, automaton_name: str):
        """Constructor of container.

        :automaton_name: Name of the automaton these declarations belong to.
        """
        self._automaton_name: str = automaton_name
        # Dictionaries relating an interface ref. name to the comm. channel name and data type
        # ROS Topics
        self._publishers: Dict[str, RosInterfaceAndType] = {}
        self._subscribers: Dict[str, RosInterfaceAndType] = {}
        # ROS Services
        self._service_servers: Dict[str, RosInterfaceAndType] = {}
        self._service_clients: Dict[str, RosInterfaceAndType] = {}
        # ROS Actions
        self._action_servers: Dict[str, RosInterfaceAndType] = {}
        self._action_clients: Dict[str, RosInterfaceAndType] = {}
        # ROS Timers
        self._timers: Dict[str, float] = {}

    def get_automaton_name(self) -> str:
        """Get name of the automaton that these declarations are defined in."""
        return self._automaton_name

    def append_publisher(self, pub_name: str, topic_name: str, topic_type: str) -> None:
        """
        Add a publisher to the container.

        :param pub_name: Name of the publisher (alias, user-defined).
        :param topic_name: Name of the topic to publish to.
        :param topic_type: Type of the message to publish.
        """
        assert all_non_empty_strings(pub_name, topic_name, topic_type), \
            "Error: ROS declarations: publisher name, topic name and type must be strings."
        assert pub_name not in self._publishers, \
            f"Error: ROS declarations: topic publisher {pub_name} already declared."
        self._publishers[pub_name] = (topic_name, topic_type)

    def append_subscriber(self, sub_name: str, topic_name: str, topic_type: str) -> None:
        """
        Add a subscriber to the container.

        :param sub_name: Name of the subscriber (alias, user-defined).
        :param topic_name: Name of the topic to subscribe to.
        :param topic_type: Type of the message to subscribe to.
        """
        assert all_non_empty_strings(sub_name, topic_name, topic_type), \
            "Error: ROS declarations: subscriber name, topic name and type must be strings."
        assert sub_name not in self._subscribers, \
            f"Error: ROS declarations: topic subscriber {sub_name} already declared."
        self._subscribers[sub_name] = (topic_name, topic_type)

    def append_service_client(self, client_name: str, service_name: str, service_type: str) -> None:
        """
        Add a service client to the container.

        :param client_name: Name of the service client (alias, user-defined).
        :param service_name: Name of the service to call.
        :param service_type: Type of data used in the service communication.
        """
        assert all_non_empty_strings(client_name, service_name, service_type), \
            "Error: ROS declarations: client name, service name and type must be strings."
        assert client_name not in self._service_clients, \
            f"Error: ROS declarations: service client {client_name} already declared."
        self._service_clients[client_name] = (service_name, service_type)

    def append_service_server(self, server_name: str, service_name: str, service_type: str) -> None:
        """
        Add a service server to the container.

        :param server_name: Name of the service server (alias, user-defined).
        :param service_name: Name of the provided service (what the client needs to call).
        :param service_type: Type of data used in the service communication.
        """
        assert all_non_empty_strings(server_name, service_name, service_type), \
            "Error: ROS declarations: server name, service name and type must be strings."
        assert server_name not in self._service_servers, \
            f"Error: ROS declarations: service server {server_name} already declared."
        self._service_servers[server_name] = (service_name, service_type)

    def append_action_client(self, client_name: str, action_name: str, action_type: str) -> None:
        assert all_non_empty_strings(client_name, action_name, action_type), \
            "Error: ROS declarations: client name, action name and type must be strings."
        assert client_name not in self._action_clients, \
            f"Error: ROS declarations: action client {client_name} already declared."
        self._action_clients[client_name] = (action_name, action_type)

    def append_action_server(self, server_name: str, action_name: str, action_type: str) -> None:
        assert all_non_empty_strings(server_name, action_name, action_type), \
            "Error: ROS declarations: server name, action name and type must be strings."
        assert server_name not in self._action_servers, \
            f"Error: ROS declarations: action server {server_name} already declared."
        self._action_servers[server_name] = (action_name, action_type)

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

    def is_service_client_defined(self, client_name: str) -> bool:
        return client_name in self._service_clients

    def is_service_server_defined(self, server_name: str) -> bool:
        return server_name in self._service_servers

    def is_action_client_defined(self, client_name: str) -> bool:
        return client_name in self._action_clients

    def is_action_server_defined(self, server_name: str) -> bool:
        return server_name in self._action_servers

    def is_timer_defined(self, timer_name: str) -> bool:
        return timer_name in self._timers

    def get_publisher_info(self, pub_name: str) -> Tuple[str, str]:
        """Provide a publisher topic name and type"""
        pub_info = self._publishers.get(pub_name)
        assert pub_info is not None, f"Error: SCXML ROS declarations: unknown publisher {pub_name}."
        return pub_info

    def get_subscriber_info(self, sub_name: str) -> Tuple[str, str]:
        """Provide a subscriber topic name and type"""
        sub_info = self._subscribers.get(sub_name)
        assert sub_info is not None, \
            f"Error: SCXML ROS declarations: unknown subscriber {sub_name}."
        return sub_info

    def get_service_server_info(self, server_name: str) -> Tuple[str, str]:
        """Provide a server's service name and type"""
        server_info = self._service_servers.get(server_name)
        assert server_info is not None, \
            f"Error: SCXML ROS declarations: unknown service server {server_name}."
        return server_info

    def get_service_client_info(self, client_name: str) -> Tuple[str, str]:
        """Provide a client's service name and type"""
        client_info = self._service_clients.get(client_name)
        assert client_info is not None, \
            f"Error: SCXML ROS declarations: unknown service client {client_name}."
        return client_info

    def get_action_server_info(self, server_name: str) -> Tuple[str, str]:
        """Given an action server name, provide the related action name and type."""
        server_info = self._action_servers.get(server_name)
        assert server_info is not None, \
            f"Error: SCXML ROS declarations: unknown action server {server_name}."
        return server_info

    def get_action_client_info(self, client_name: str) -> Tuple[str, str]:
        """Given an action client name, provide the related action name and type."""
        client_info = self._action_clients.get(client_name)
        assert client_info is not None, \
            f"Error: SCXML ROS declarations: unknown action client {client_name}."
        return client_info

    def get_timers(self) -> Dict[str, float]:
        return self._timers

    def check_valid_srv_req_fields(self, client_name: str, ros_fields: List[RosField]) -> bool:
        """Check if the provided fields match the service request type."""
        _, service_type = self.get_service_client_info(client_name)
        req_fields, _ = get_srv_type_params(service_type)
        if not check_all_fields_known(ros_fields, req_fields):
            print(f"Error: SCXML ROS declarations: Srv request {client_name} has invalid fields.")
            return False
        return True

    def check_valid_srv_res_fields(self, server_name: str, ros_fields: List[RosField]) -> bool:
        """Check if the provided fields match the service response type."""
        _, res_type = self.get_service_server_info(server_name)
        _, res_fields = get_srv_type_params(res_type)
        if not check_all_fields_known(ros_fields, res_fields):
            print(f"Error: SCXML ROS declarations: Srv response {server_name} has invalid fields.")
            return False
        return True

    def check_valid_action_goal_fields(self, client_name: str, ros_fields: List[RosField]) -> bool:
        """Check if the provided fields match the action goal type."""
        _, action_type = self.get_action_client_info(client_name)
        goal_fields, _, _ = get_action_type_params(action_type)
        if not check_all_fields_known(ros_fields, goal_fields):
            print(f"Error: SCXML ROS declarations: Action goal {client_name} has invalid fields.")
            return False
        return True

    def check_valid_action_feedback_fields(
            self, server_name: str, ros_fields: List[RosField]) -> bool:
        """Check if the provided fields match the action feedback type."""
        _, action_type = self.get_action_server_info(server_name)
        _, feedback_fields, _ = get_action_type_params(action_type)
        if not check_all_fields_known(ros_fields, feedback_fields):
            print(f"Error: SCXML ROS declarations: Action feedback {server_name} "
                  "has invalid fields.")
            return False
        return True

    def check_valid_action_result_fields(
            self, server_name: str, ros_fields: List[RosField]) -> bool:
        """Check if the provided fields match the action result type."""
        _, action_type = self.get_action_server_info(server_name)
        _, _, result_fields = get_action_type_params(action_type)
        if not check_all_fields_known(ros_fields, result_fields):
            print(f"Error: SCXML ROS declarations: Action result {server_name} has invalid fields.")
            return False
        return True
