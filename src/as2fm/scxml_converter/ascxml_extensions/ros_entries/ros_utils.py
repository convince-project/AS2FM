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

import re
from typing import Any, Dict, List, Optional, Tuple, Type

from as2fm.as2fm_common.logging import get_error_msg
from as2fm.scxml_converter.ascxml_extensions.ros_entries.scxml_ros_field import RosField
from as2fm.scxml_converter.scxml_entries.utils import get_plain_variable_name

MSG_TYPE_SUBSTITUTIONS = {
    "boolean": "bool",
    "float": "float32",
    "double": "float64",
    "sequence<int32>": "int32[]",
    "sequence<float>": "float32[]",
    "sequence<double>": "float64[]",
}

BASIC_FIELD_TYPES = [
    "boolean",
    "int8",
    "int16",
    "int32",
    "int64",
    "float",
    "double",
    "string",
    "sequence<int32>",
    "sequence<float>",
    "sequence<double>",
]

# Collection of all the prefixes related to each ROS interface
ROS_INTERFACE_TO_PREFIXES = {
    "ros_timer": [],
    "ros_topic": ["_msg."],
    "ros_service_request": ["_req."],
    "ros_service_result": ["_res."],
    "ros_action_goal": ["_action.goal_id", "_goal."],
    "ros_action_result": ["_action.goal_id", "_wrapped_result.code", "_wrapped_result.result."],
    "ros_action_feedback": ["_action.goal_id", "_feedback."],
}


def import_ros_type(type_definition: str, ros_interface: str) -> Optional[Type]:
    """
    Try to import a ROS definition (msg, srv or action).

    :param type_definition: The type definition to check (e.g. std_msgs/Empty).
    :param ros_interface: msg, srv or action.
    :return The loaded interface in case of success. None in case the interface does not exist.
    """
    assert (
        isinstance(type_definition, str) and type_definition.count("/") == 1
    ), f"Unexpected {type_definition=}"
    interface_ns, interface_type = type_definition.split("/")
    assert len(interface_ns) > 0 and len(interface_type) > 0, f"Invalid {type_definition=}"
    assert ros_interface in [
        "msg",
        "srv",
        "action",
    ], f"Error: SCXML ROS declarations: unknown ROS interface {ros_interface}."
    try:
        interface_importer = __import__(interface_ns + f".{ros_interface}", fromlist=[""])
        loaded_interface = getattr(interface_importer, interface_type)
    except (ImportError, AttributeError):
        return None
    return loaded_interface


def is_ros_type_known(type_definition: str, ros_interface: str) -> bool:
    """
    Check if python can import the provided type definition.

    :param type_definition: The type definition to check (e.g. std_msgs/Empty).
    """
    return import_ros_type(type_definition, ros_interface) is not None


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
    fields: Dict[str, str] = ros_interface_type.get_fields_and_field_types()
    proc_fields: Dict[str, str] = {}
    for field_key, field_type in fields.items():
        if field_type in BASIC_FIELD_TYPES:
            proc_fields[field_key] = MSG_TYPE_SUBSTITUTIONS.get(field_type, field_type)
        elif "/" in field_type:
            assert not field_type.startswith(
                "sequence<"
            ), f"Error: cannot handle yet array of custom msg types '{field_type}'"
            custom_msg_type = import_ros_type(field_type, "msg")
            assert custom_msg_type is not None, f"Error: unknown msg subtype {field_type}."
            key_sub_fields = extract_params_from_ros_type(custom_msg_type)
            for subkey, subtype in key_sub_fields.items():
                proc_fields[f"{field_key}.{subkey}"] = subtype
    return proc_fields


def check_all_fields_known(ros_fields: List[RosField], field_types: Dict[str, str]) -> bool:
    """
    Check that all fields from ros_fields are in field_types, and that no field is missing.
    """
    for ros_field in ros_fields:
        if ros_field.get_name() not in field_types:
            get_error_msg(
                ros_field.get_xml_origin(), "Unknown field to the related ROS declaration."
            )
            return False
        field_types.pop(ros_field.get_name())
    if len(field_types) > 0:
        missing_fields = ""
        for field_key in field_types.keys():
            missing_fields += f"{field_key}, "
        missing_fields = missing_fields.removesuffix(", ")
        get_error_msg(
            ros_fields[0].get_xml_origin(), f"There are missing ROS fields: [{missing_fields}]"
        )
        return False
    return True


def get_plain_ros_param_dict(type_params: Dict[str, str]) -> Dict[str, str]:
    """Replace the keys in the ROS type params dict with the default separator."""
    return {get_plain_variable_name(key, None): val for key, val in type_params.items()}


def get_msg_type_params(topic_definition: str) -> Dict[str, str]:
    """Get the fields of a ROS message type, usually related to a topic."""
    ros_msg_type = import_ros_type(topic_definition, "msg")
    assert (
        ros_msg_type is not None
    ), f"Error: SCXML ROS declarations: msg type {topic_definition} not found."
    return extract_params_from_ros_type(ros_msg_type)


def get_srv_type_params(service_definition: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Get the fields of a service request and response as pairs of name and type objects.
    """
    srv_data_type = import_ros_type(service_definition, "srv")
    assert (
        srv_data_type is not None
    ), f"Error: SCXML ROS declarations: service type {service_definition} not found."
    req_fields = extract_params_from_ros_type(srv_data_type.Request)
    res_fields = extract_params_from_ros_type(srv_data_type.Response)
    return req_fields, res_fields


def get_action_type_params(
    action_definition: str,
) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """
    Get the fields of an action goal, feedback and result as pairs of name and type objects.
    """
    action_data_type = import_ros_type(action_definition, "action")
    assert (
        action_data_type is not None
    ), f"Error: SCXML ROS declarations: action type {action_definition} not found."
    action_goal_fields = extract_params_from_ros_type(action_data_type.Goal)
    action_feedback_fields = extract_params_from_ros_type(action_data_type.Feedback)
    action_result_fields = extract_params_from_ros_type(action_data_type.Result)
    return action_goal_fields, action_feedback_fields, action_result_fields


def get_action_goal_id_definition() -> Tuple[str, str]:
    """Provide the definition of the goal_id field in ROS actions."""
    return "goal_id", "int32"


def sanitize_ros_interface_name(interface_name: str) -> str:
    """Replace slashes in a ROS interface name."""
    assert isinstance(
        interface_name, str
    ), "Error: ROS interface sanitizer: interface name must be a string."
    # Remove potential prepended slash
    interface_name = interface_name.removeprefix("/")
    assert (
        len(interface_name) > 0
    ), "Error: ROS interface sanitizer: interface name must not be empty."
    assert (
        interface_name.count(" ") == 0
    ), "Error: ROS interface sanitizer: interface name must not contain spaces."
    return interface_name.replace("/", "__")


def generate_rate_timer_event(timer_name: str) -> str:
    """Generate the name of the event triggered by a rate timer."""
    # TODO: Remove dot notation
    return f"ros_time_rate.{timer_name}"


def generate_topic_event(topic_name: str) -> str:
    """Generate the name of the event that triggers a message reception from a topic."""
    return f"topic_{sanitize_ros_interface_name(topic_name)}_msg"


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


def is_srv_event(event_name) -> bool:
    """Check whether the event name matches the ROS service plain events pattern."""
    return re.match(r"^srv_.+_(response|request|req_client).*$", event_name) is not None


def generate_action_goal_req_event(action_name: str, client_name: str) -> str:
    """Generate the name of the event that sends an action goal from a client to the server."""
    return f"action_{sanitize_ros_interface_name(action_name)}_goal_req_client_{client_name}"


def generate_action_goal_accepted_event(action_name: str) -> str:
    """Generate the name of the event sent from the server in case of goal acceptance."""
    return f"action_{sanitize_ros_interface_name(action_name)}_goal_accepted"


def generate_action_goal_rejected_event(action_name: str) -> str:
    """Generate the name of the event sent from the server in case of goal rejection."""
    return f"action_{sanitize_ros_interface_name(action_name)}_goal_rejected"


def generate_action_goal_handle_event(action_name: str) -> str:
    """Generate the name of the event that triggers an action goal handling in the server."""
    return f"action_{sanitize_ros_interface_name(action_name)}_goal_handle"


def generate_action_goal_handle_accepted_event(action_name: str, client_name: str) -> str:
    """Generate the name of the event that reports goal acceptance to a client."""
    return f"action_{sanitize_ros_interface_name(action_name)}_goal_accept_client_{client_name}"


def generate_action_goal_handle_rejected_event(action_name: str, client_name: str) -> str:
    """Generate the name of the event that reports goal rejection to a client."""
    return f"action_{sanitize_ros_interface_name(action_name)}_goal_reject_client_{client_name}"


def generate_action_thread_execution_start_event(action_name: str) -> str:
    """Generate the name of the event that triggers the start of an action thread execution."""
    return f"action_{sanitize_ros_interface_name(action_name)}_thread_start"


def generate_action_thread_free_event(action_name: str) -> str:
    """Generate the name of the event sent when an action thread becomes free."""
    return f"action_{sanitize_ros_interface_name(action_name)}_thread_free"


def generate_action_feedback_event(action_name: str) -> str:
    """Generate the name of the event that sends a feedback from the action server."""
    return f"action_{sanitize_ros_interface_name(action_name)}_feedback"


def generate_action_feedback_handle_event(action_name: str, automaton_name: str) -> str:
    """Generate the name of the event that handles a feedback in an action client."""
    return (
        f"action_{sanitize_ros_interface_name(action_name)}_"
        f"feedback_handle_client_{automaton_name}"
    )


def generate_action_result_event(action_name: str) -> str:
    """Generate the name of the event that sends a result from the action server."""
    return f"action_{sanitize_ros_interface_name(action_name)}_result"


def generate_action_result_handle_event(action_name: str, automaton_name: str) -> str:
    """Generate the name of the event that handles a result in an action client."""
    return (
        f"action_{sanitize_ros_interface_name(action_name)}_"
        f"result_handle_client_{automaton_name}"
    )


def is_action_request_event(event_name: str) -> bool:
    """Check whether the event name matches the ROS action plain events pattern."""
    return re.match(r"^action_.+_goal_.+$", event_name) is not None


def is_action_result_event(event_name: str) -> bool:
    """Check whether the event name matches the ROS action plain events pattern."""
    return re.match(r"^action_.+_result.*$", event_name) is not None


def is_action_thread_event(event_name: str) -> bool:
    """Check whether the event name matches the ROS action plain events pattern."""
    return re.match(r"^action_.+_thread_(start|free)$", event_name) is not None
