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

"""Collection of various utilities for scxml entries."""

from typing import Dict, List, Optional, Tuple

from scxml_converter.scxml_entries.scxml_ros_field import RosField

MSG_TYPE_SUBSTITUTIONS = {
    "boolean": "bool",
}

BASIC_FIELD_TYPES = ['boolean',
                     'int8', 'int16', 'int32', 'int64',
                     'float', 'double']

# TODO: add lower and upper bounds depending on the n. of bits used.
# TODO: add support to uint
SCXML_DATA_STR_TO_TYPE = {
    "bool": bool,
    "float32": float,
    "float64": float,
    "int8": int,
    "int16": int,
    "int32": int,
    "int64": int
}


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


def is_action_type_known(service_definition: str) -> bool:
    """Check if python can import the provided service definition."""
    return is_ros_type_known(service_definition, "action")


def get_srv_type_params(service_definition: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Get the data fields of a service request and response type as pairs of name and type objects.
    """
    assert is_srv_type_known(service_definition), \
        "Error: SCXML ROS declarations: service type not found."
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


def get_action_type_params(action_definition: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Get the data fields of a action request and response type as pairs of name and type objects.

    :return: goal, feedback, result
    """
    assert is_action_type_known(action_definition), \
        "Error: SCXML ROS declarations: action type not found."
    interface_ns, interface_type = action_definition.split("/")
    action_module = __import__(interface_ns + '.action', fromlist=[''])
    action_class = getattr(action_module, interface_type)

    # TODO: Fields can be nested. Look AS2FM/scxml_converter/src/scxml_converter/scxml_converter.py
    goal = action_class.Goal.get_fields_and_field_types()
    for key in goal.keys():
        # TODO: Support nested fields
        assert goal[key] in BASIC_FIELD_TYPES, \
            f"Error: SCXML ROS declarations: action goal type {goal[key]} isn't a basic field."
        goal[key] = MSG_TYPE_SUBSTITUTIONS.get(goal[key], goal[key])

    feedback = action_class.Feedback.get_fields_and_field_types()
    for key in feedback.keys():
        assert feedback[key] in BASIC_FIELD_TYPES, \
            "Error: SCXML ROS declarations: action feedback type contains non-basic fields."
        feedback[key] = MSG_TYPE_SUBSTITUTIONS.get(feedback[key], feedback[key])

    result = action_class.Result.get_fields_and_field_types()
    for key in result.keys():
        assert result[key] in BASIC_FIELD_TYPES, \
            "Error: SCXML ROS declarations: action result type contains non-basic fields."
        result[key] = MSG_TYPE_SUBSTITUTIONS.get(result[key], result[key])

    return goal, feedback, result


def replace_ros_interface_expression(msg_expr: str) -> str:
    """
    Convert a ROS interface expression (msg, req, res, goal, feedback, result) to plain SCXML
    (event).
    """
    scxml_prefix = "_event."
    # TODO: Use regex and ensure no other valid character exists before the initial underscore
    for ros_prefix in [
            "_msg.",  # topics
            "_req.",  # services
            "_res.",  # services
            "_goal.",  # actions
            "_feedback.",  # actions
            "_result."  # actions
    ]:
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


def get_default_expression_for_type(field_type: str) -> str:
    """Generate a default expression for a field type."""
    return str(SCXML_DATA_STR_TO_TYPE[field_type]())


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
        # Dict of publishers and subscribers: topic name -> type
        self._publishers: Dict[str, str] = {}
        self._subscribers: Dict[str, str] = {}
        self._service_servers: Dict[str, str] = {}
        self._service_clients: Dict[str, str] = {}
        self._action_servers: Dict[str, str] = {}
        self._action_clients: Dict[str, str] = {}
        self._timers: Dict[str, float] = {}

    def get_automaton_name(self) -> str:
        """Get name of the automaton that these declarations are defined in."""
        return self._automaton_name

    def append_publisher(self, topic_name: str, topic_type: str) -> None:
        assert isinstance(topic_name, str) and isinstance(topic_type, str), \
            "Error: ROS declarations: topic name and type must be strings."
        assert topic_name not in self._publishers, \
            f"Error: ROS declarations: topic publisher {topic_name} already declared."
        self._publishers[topic_name] = topic_type

    def append_subscriber(self, topic_name: str, topic_type: str) -> None:
        assert isinstance(topic_name, str) and isinstance(topic_type, str), \
            "Error: ROS declarations: topic name and type must be strings."
        assert topic_name not in self._subscribers, \
            f"Error: ROS declarations: topic subscriber {topic_name} already declared."
        self._subscribers[topic_name] = topic_type

    def append_service_client(self, service_name: str, service_type: str) -> None:
        assert isinstance(service_name, str) and isinstance(service_type, str), \
            "Error: ROS declarations: service name and type must be strings."
        assert service_name not in self._service_clients, \
            f"Error: ROS declarations: service client {service_name} already declared."
        self._service_clients[service_name] = service_type

    def append_service_server(self, service_name: str, service_type: str) -> None:
        assert isinstance(service_name, str) and isinstance(service_type, str), \
            "Error: ROS declarations: service name and type must be strings."
        assert service_name not in self._service_servers, \
            f"Error: ROS declarations: service server {service_name} already declared."
        self._service_servers[service_name] = service_type

    def append_action_client(self, action_name: str, action_type: str) -> None:
        assert isinstance(action_name, str) and isinstance(action_type, str), \
            "Error: ROS declarations: action name and type must be strings."
        assert action_name not in self._action_clients, \
            f"Error: ROS declarations: action client {action_name} already declared."
        self._action_clients[action_name] = action_type

    def append_action_server(self, action_name: str, action_type: str) -> None:
        assert isinstance(action_name, str) and isinstance(action_type, str), \
            "Error: ROS declarations: action name and type must be strings."
        assert action_name not in self._action_servers, \
            f"Error: ROS declarations: action server {action_name} already declared."
        self._action_servers[action_name] = action_type

    def append_timer(self, timer_name: str, timer_rate: float) -> None:
        assert isinstance(timer_name, str), "Error: ROS declarations: timer name must be a string."
        assert isinstance(timer_rate, float) and timer_rate > 0, \
            "Error: ROS declarations: timer rate must be a positive number."
        assert timer_name not in self._timers, \
            f"Error: ROS declarations: timer {timer_name} already declared."
        self._timers[timer_name] = timer_rate

    def is_publisher_defined(self, topic_name: str) -> bool:
        return topic_name in self._publishers

    def is_subscriber_defined(self, topic_name: str) -> bool:
        return topic_name in self._subscribers

    def is_timer_defined(self, timer_name: str) -> bool:
        return timer_name in self._timers

    def get_timers(self) -> Dict[str, float]:
        return self._timers

    def is_service_client_defined(self, service_name: str) -> bool:
        return service_name in self._service_clients

    def is_service_server_defined(self, service_name: str) -> bool:
        return service_name in self._service_servers

    def get_service_client_type(self, service_name: str) -> Optional[str]:
        return self._service_clients.get(service_name, None)

    def get_service_server_type(self, service_name: str) -> Optional[str]:
        return self._service_servers.get(service_name, None)

    def is_action_client_defined(self, action_name: str) -> bool:
        return action_name in self._action_clients

    def is_action_server_defined(self, action_name: str) -> bool:
        return action_name in self._action_servers

    def get_action_client_type(self, action_name: str) -> Optional[str]:
        return self._action_clients.get(action_name, None)

    def get_action_server_type(self, action_name: str) -> Optional[str]:
        return self._action_servers.get(action_name, None)

    def check_valid_srv_req_fields(self, service_name: str, ros_fields: List[RosField]) -> bool:
        """Check if the provided fields match the service request type."""
        req_type = self.get_service_client_type(service_name)
        if req_type is None:
            print(f"Error: SCXML ROS declarations: unknown service client {service_name}.")
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

    def check_valid_srv_res_fields(self, service_name: str, ros_fields: List[RosField]) -> bool:
        """Check if the provided fields match the service response type."""
        res_type = self.get_service_server_type(service_name)
        if res_type is None:
            print(f"Error: SCXML ROS declarations: unknown service server {service_name}.")
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

    def check_valid_action_goal_fields(self, service_name: str, ros_fields: List[RosField]) -> bool:
        """Check if the provided fields match the service goal type."""
        goal_type = self.get_service_client_type(service_name)
        if goal_type is None:
            print(f"Error: SCXML ROS declarations: unknown service client {service_name}.")
            return False
        goal_fields, _, _ = get_action_type_params(goal_type)
        for ros_field in ros_fields:
            if ros_field.get_name() not in goal_fields:
                print("Error: SCXML ROS declarations: "
                      f"unknown field {ros_field.get_name()} in service goal.")
                return False
            goal_fields.pop(ros_field.get_name())
        if len(goal_fields) > 0:
            print("Error: SCXML ROS declarations: missing fields in service goal.")
            for goal_field in goal_fields.keys():
                print(f"\t-{goal_field}.")
            return False
        return True

    def check_valid_action_feedback_fields(
            self, service_name: str, ros_fields: List[RosField]) -> bool:
        """Check if the provided fields match the service feedback type."""
        feedback_type = self.get_service_client_type(service_name)
        if feedback_type is None:
            print(f"Error: SCXML ROS declarations: unknown service client {service_name}.")
            return False
        _, feedback_fields, _ = get_action_type_params(feedback_type)
        for ros_field in ros_fields:
            if ros_field.get_name() not in feedback_fields:
                print("Error: SCXML ROS declarations: "
                      f"unknown field {ros_field.get_name()} in service feedback.")
                return False
            feedback_fields.pop(ros_field.get_name())
        if len(feedback_fields) > 0:
            print("Error: SCXML ROS declarations: missing fields in service feedback.")
            for feedback_field in feedback_fields.keys():
                print(f"\t-{feedback_field}.")
            return False
        return True

    def check_valid_action_result_fields(
            self, service_name: str, ros_fields: List[RosField]) -> bool:
        """Check if the provided fields match the service result type."""
        result_type = self.get_service_client_type(service_name)
        if result_type is None:
            print(f"Error: SCXML ROS declarations: unknown service client {service_name}.")
            return False
        _, result_fields, _ = get_action_type_params(result_type)
        for ros_field in ros_fields:
            if ros_field.get_name() not in result_fields:
                print("Error: SCXML ROS declarations: "
                      f"unknown field {ros_field.get_name()} in service result.")
                return False
            result_fields.pop(ros_field.get_name())
        if len(result_fields) > 0:
            print("Error: SCXML ROS declarations: missing fields in service result.")
            for result_field in result_fields.keys():
                print(f"\t-{result_field}.")
            return False
        return True
