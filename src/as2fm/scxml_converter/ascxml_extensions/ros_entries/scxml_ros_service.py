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
Declaration of SCXML tags related to ROS Services.

Additional information:
https://docs.ros.org/en/iron/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Services/Understanding-ROS2-Services.html
"""

from typing import List, Type

from as2fm.as2fm_common.logging import log_error
from as2fm.scxml_converter.ascxml_extensions.ros_entries.ros_utils import (
    ROS_INTERFACE_TO_PREFIXES,
    check_all_fields_known,
    generate_srv_request_event,
    generate_srv_response_event,
    generate_srv_server_request_event,
    generate_srv_server_response_event,
    get_srv_type_params,
    is_srv_type_known,
)
from as2fm.scxml_converter.ascxml_extensions.ros_entries.scxml_ros_base import (
    RosCallback,
    RosDeclaration,
    RosTrigger,
)
from as2fm.scxml_converter.scxml_entries import AscxmlDeclaration


class RosServiceServer(RosDeclaration):
    """Object used in SCXML root to declare a new service server."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_service_server"

    @staticmethod
    def get_communication_interface() -> str:
        return "service"

    def check_valid_interface_type(self) -> bool:
        if not is_srv_type_known(self._interface_type):
            log_error(
                self.get_xml_origin(),
                f"Invalid service type {self._interface_type}.",
            )
            return False
        return True


class RosServiceClient(RosDeclaration):
    """Object used in SCXML root to declare a new service client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_service_client"

    @staticmethod
    def get_communication_interface() -> str:
        return "service"

    def check_valid_interface_type(self) -> bool:
        if not is_srv_type_known(self._interface_type):
            log_error(
                self.get_xml_origin(),
                f"Invalid service type {self._interface_type}.",
            )
            return False
        return True


class RosServiceSendRequest(RosTrigger):
    """Object representing a ROS service request (from the client side) in SCXML."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_service_send_request"

    @staticmethod
    def get_declaration_type() -> Type[RosServiceClient]:
        return RosServiceClient

    def check_fields_validity(self, ascxml_declaration: AscxmlDeclaration) -> bool:
        assert isinstance(ascxml_declaration, RosServiceClient)
        result_fields = get_srv_type_params(ascxml_declaration.get_interface_type())[0]
        return check_all_fields_known(self._params, result_fields)

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosServiceClient)
        return generate_srv_request_event(
            ascxml_declaration.get_interface_name(),
            ascxml_declaration.get_node_name(),
        )


class RosServiceHandleRequest(RosCallback):
    """SCXML object representing a ROS service callback on the server, acting upon a request."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_service_handle_request"

    @staticmethod
    def get_declaration_type() -> Type[RosServiceServer]:
        return RosServiceServer

    @staticmethod
    def get_callback_prefixes() -> List[str]:
        return ROS_INTERFACE_TO_PREFIXES["ros_service_request"]

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosServiceServer)
        return generate_srv_server_request_event(ascxml_declaration.get_interface_name())


class RosServiceSendResponse(RosTrigger):
    """SCXML object representing the response from a service server."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_service_send_response"

    @staticmethod
    def get_declaration_type() -> Type[RosServiceServer]:
        return RosServiceServer

    def check_fields_validity(self, ascxml_declaration: AscxmlDeclaration) -> bool:
        assert isinstance(ascxml_declaration, RosServiceServer)
        result_fields = get_srv_type_params(ascxml_declaration.get_interface_type())[1]
        return check_all_fields_known(self._params, result_fields)

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosServiceServer)
        return generate_srv_server_response_event(ascxml_declaration.get_interface_name())


class RosServiceHandleResponse(RosCallback):
    """SCXML object representing the handler of a service response for a service client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_service_handle_response"

    @staticmethod
    def get_declaration_type() -> Type[RosServiceClient]:
        return RosServiceClient

    @staticmethod
    def get_callback_prefixes() -> List[str]:
        return ROS_INTERFACE_TO_PREFIXES["ros_service_result"]

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosServiceClient)
        return generate_srv_response_event(
            ascxml_declaration.get_interface_name(),
            ascxml_declaration.get_node_name(),
        )
