# Copyright (c) 2026 - for information on the respective copyright owner
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

from typing import Dict, List, Optional

from as2fm.jani_generator.ros_helpers.ros_action_handler import RosActionHandler
from as2fm.jani_generator.ros_helpers.ros_service_handler import RosServiceHandler

from as2fm.scxml_converter.ascxml_extensions.ros_entries.ros_event_info import RosEventInfo
from as2fm.scxml_converter.ascxml_extensions.ros_entries.ros_utils import (
    generate_action_feedback_event,
    generate_action_feedback_handle_event,
    generate_action_goal_accepted_event,
    generate_action_goal_handle_accepted_event,
    generate_action_goal_handle_event,
    generate_action_goal_handle_rejected_event,
    generate_action_goal_rejected_event,
    generate_action_goal_req_event,
    generate_action_result_event,
    generate_action_result_handle_event,
    generate_srv_request_event,
    generate_srv_response_event,
    generate_srv_server_request_event,
    generate_srv_server_response_event,
    generate_topic_event,
    get_action_type_params,
    get_msg_type_params,
    get_srv_type_params,
    sanitize_ros_interface_name,
)
from as2fm.scxml_converter.data_types.type_utils import MEMBER_ACCESS_SUBSTITUTION
from as2fm.scxml_converter.scxml_entries.utils import ASCXML_FIELD_PREFIX


class DataToRosInfoTransformer:
    """
    Generates a list of RosEventInfo from collected information about ROS communications.
    """
    def __init__(self, 
                 topic_info: Optional[Dict[str, Dict]] = None, 
                 service_info: Optional[Dict[str, Dict]] = None, 
                 action_info: Optional[Dict[str, Dict]] = None,
                ):
        self._ros_events_info = []
        self._topic_info = topic_info
        self._service_info = service_info
        self._action_info = action_info


    def transform_data(self) -> List:
        if self._topic_info is not None:
            self._transform_topic_info()

        if self._service_info is not None:
            self._transform_service_info()

        if self._action_info is not None:
            self._transform_action_info()

        return self._ros_events_info


    def _transform_topic_info(self):
        for interface_name, info in self._topic_info.items():
            sanitized_name = sanitize_ros_interface_name(interface_name)
            msg_fields = get_msg_type_params(info["type"])
            field_names = [{name: self._to_scxml_field_name(name)} for name in msg_fields.keys()]
            event_name = generate_topic_event(interface_name)
            if not info["subscribers"]:
                info["subscribers"].append("NONE")
            for pub in info["publishers"]:
                for sub in info["subscribers"]:
                    self._ros_events_info.append(
                        RosEventInfo(
                            interface_name=sanitized_name,
                            interface_type="topic",
                            scxml_event_name=event_name,
                            event_type="publish",
                            origin=pub,
                            target=sub,
                            fields=field_names,
                        )
                    )

    def _transform_service_info(self):
        for interface_name, info in self._service_info.items():
            sanitized_name = sanitize_ros_interface_name(interface_name)
            req_fields, res_fields = get_srv_type_params(info["type"])
            req_field_names = [{name: self._to_scxml_field_name(name)} for name in req_fields.keys()]
            res_field_names = [{name: self._to_scxml_field_name(name)} for name in res_fields.keys()]
            server = info["server"]
            handler = RosServiceHandler.get_interface_prefix() + sanitized_name
            for client in info["clients"]:
                self._ros_events_info.append(
                    RosEventInfo(
                        interface_name=sanitized_name,
                        interface_type="service",
                        scxml_event_name=generate_srv_request_event(interface_name, client),
                        event_type="request",
                        origin=client,
                        target=handler,
                        fields=req_field_names,
                    )
                )
                self._ros_events_info.append(
                    RosEventInfo(
                        interface_name=sanitized_name,
                        interface_type="service",
                        scxml_event_name=generate_srv_response_event(interface_name, client),
                        event_type="response",
                        origin=handler,
                        target=client,
                        fields=res_field_names,
                    )
                )
            self._ros_events_info.append(
                RosEventInfo(
                    interface_name=sanitized_name,
                    interface_type="service",
                    scxml_event_name=generate_srv_server_request_event(interface_name),
                    event_type="request",
                    origin=handler,
                    target=server,
                    fields=req_field_names,
                )
            )
            self._ros_events_info.append(
                RosEventInfo(
                    interface_name=sanitized_name,
                    interface_type="service",
                    scxml_event_name=generate_srv_server_response_event(interface_name),
                    event_type="response",
                    origin=server,
                    target=handler,
                    fields=res_field_names,
                )
            )

    def _transform_action_info(self):
        for interface_name, info in self._action_info.items():
            sanitized_name = sanitize_ros_interface_name(interface_name)
            goal_fields, feedback_fields, result_fields = get_action_type_params(info["type"])
            goal_field_names = [{name: self._to_scxml_field_name(name)} for name in goal_fields.keys()]
            feedback_field_names = [{name: self._to_scxml_field_name(name)} for name in feedback_fields.keys()]
            result_field_names = [{name: self._to_scxml_field_name(name)} for name in result_fields.keys()]
            server = info["server"]
            handler = RosActionHandler.get_interface_prefix() + sanitized_name
            for client in info["clients"]:
                self._ros_events_info.append(
                    RosEventInfo(
                        interface_name=sanitized_name,
                        interface_type="action",
                        scxml_event_name=generate_action_goal_req_event(interface_name, client),
                        event_type="goal_request",
                        origin=client,
                        target=handler,
                        fields=goal_field_names,
                    )
                )
                self._ros_events_info.append(
                    RosEventInfo(
                        interface_name=sanitized_name,
                        interface_type="action",
                        scxml_event_name=generate_action_goal_handle_accepted_event(
                            interface_name, client
                        ),
                        event_type="goal_response",
                        origin=handler,
                        target=client,
                    )
                )
                self._ros_events_info.append(
                    RosEventInfo(
                        interface_name=sanitized_name,
                        interface_type="action",
                        scxml_event_name=generate_action_goal_handle_rejected_event(
                            interface_name, client
                        ),
                        event_type="goal_response",
                        origin=handler,
                        target=client,
                    )
                )
                self._ros_events_info.append(
                    RosEventInfo(
                        interface_name=sanitized_name,
                        interface_type="action",
                        scxml_event_name=generate_action_feedback_handle_event(
                            interface_name, client
                        ),
                        event_type="feedback",
                        origin=handler,
                        target=client,
                        fields=feedback_field_names,
                    )
                )
                self._ros_events_info.append(
                    RosEventInfo(
                        interface_name=sanitized_name,
                        interface_type="action",
                        scxml_event_name=generate_action_result_handle_event(
                            interface_name, client
                        ),
                        event_type="result",
                        origin=handler,
                        target=client,
                        fields=result_field_names,
                    )
                )

            self._ros_events_info.append(
                RosEventInfo(
                    interface_name=sanitized_name,
                    interface_type="action",
                    scxml_event_name=generate_action_goal_accepted_event(interface_name),
                    event_type="goal_response",
                    origin=server,
                    target=handler,
                )
            )
            self._ros_events_info.append(
                RosEventInfo(
                    interface_name=sanitized_name,
                    interface_type="action",
                    scxml_event_name=generate_action_goal_rejected_event(interface_name),
                    event_type="goal_response",
                    origin=server,
                    target=handler,
                )
            )
            self._ros_events_info.append(
                RosEventInfo(
                    interface_name=sanitized_name,
                    interface_type="action",
                    scxml_event_name=generate_action_goal_handle_event(interface_name),
                    event_type="goal_request",
                    origin=handler,
                    target=server,
                    fields=goal_field_names,
                )
            )
            self._ros_events_info.append(
                RosEventInfo(
                    interface_name=sanitized_name,
                    interface_type="action",
                    scxml_event_name=generate_action_feedback_event(interface_name),
                    event_type="feedback",
                    origin=server,
                    target=handler,
                    fields=feedback_field_names,
                )
            )
            self._ros_events_info.append(
                RosEventInfo(
                    interface_name=sanitized_name,
                    interface_type="action",
                    scxml_event_name=generate_action_result_event(interface_name),
                    event_type="result",
                    origin=server,
                    target=handler,
                    fields=result_field_names,
                )
            )

    @staticmethod
    def _to_scxml_field_name(field_name: str) -> str:
        return ASCXML_FIELD_PREFIX + field_name.replace(".", MEMBER_ACCESS_SUBSTITUTION)
