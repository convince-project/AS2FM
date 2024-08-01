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

from typing import Dict, Tuple


MSG_TYPE_SUBSTITUTIONS = {
    "boolean": "bool",
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
        req[key] = MSG_TYPE_SUBSTITUTIONS.get(req[key], req[key])

    res = srv_class.Response.get_fields_and_field_types()
    for key in res.keys():
        res[key] = MSG_TYPE_SUBSTITUTIONS.get(res[key], res[key])

    return req, res


def replace_ros_msg_expression(msg_expr: str) -> str:
    """Convert a ROS message expression (referring to ROS msg entries) to plain SCXML."""
    prefix = "_event." if msg_expr.startswith("_msg.") else ""
    return prefix + msg_expr.removeprefix("_msg.")


class ScxmlRosDeclarationsContainer:
    """Object that contains a description of the ROS declarations in the SCXML root."""

    def __init__(self):
        # Dict of publishers and subscribers: topic name -> type
        self._publishers: Dict[str, str] = {}
        self._subscribers: Dict[str, str] = {}
        self._service_servers: Dict[str, str] = {}
        self._service_clients: Dict[str, str] = {}
        self._timers: Dict[str, float] = {}

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
