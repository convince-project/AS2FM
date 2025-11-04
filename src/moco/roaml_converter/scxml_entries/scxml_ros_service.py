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

from typing import Type

from moco.roaml_converter.scxml_entries import ScxmlRosDeclarationsContainer
from moco.roaml_converter.scxml_entries.ros_utils import (
    generate_srv_request_event,
    generate_srv_response_event,
    generate_srv_server_request_event,
    generate_srv_server_response_event,
    is_srv_type_known,
)
from moco.roaml_converter.scxml_entries.scxml_ros_base import (
    RosCallback,
    RosDeclaration,
    RosTrigger,
)
from moco.roaml_converter.scxml_entries.utils import CallbackType


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
            print("Error: SCXML RosServiceServer: service type is not valid.")
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
            print("Error: SCXML RosServiceClient: service type is not valid.")
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

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_service_client_defined(self._interface_name)

    def check_fields_validity(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.check_valid_srv_req_fields(self._interface_name, self._fields)

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_srv_request_event(
            ros_declarations.get_service_client_info(self._interface_name)[0],
            ros_declarations.get_automaton_name(),
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
    def get_callback_type() -> CallbackType:
        return CallbackType.ROS_SERVICE_REQUEST

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_service_server_defined(self._interface_name)

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_srv_server_request_event(
            ros_declarations.get_service_server_info(self._interface_name)[0]
        )


class RosServiceSendResponse(RosTrigger):
    """SCXML object representing the response from a service server."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_service_send_response"

    @staticmethod
    def get_declaration_type() -> Type[RosServiceServer]:
        return RosServiceServer

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_service_server_defined(self._interface_name)

    def check_fields_validity(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.check_valid_srv_res_fields(self._interface_name, self._fields)

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_srv_server_response_event(
            ros_declarations.get_service_server_info(self._interface_name)[0]
        )


class RosServiceHandleResponse(RosCallback):
    """SCXML object representing the handler of a service response for a service client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_service_handle_response"

    @staticmethod
    def get_declaration_type() -> Type[RosServiceClient]:
        return RosServiceClient

    @staticmethod
    def get_callback_type() -> CallbackType:
        return CallbackType.ROS_SERVICE_RESULT

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_service_client_defined(self._interface_name)

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_srv_response_event(
            ros_declarations.get_service_client_info(self._interface_name)[0],
            ros_declarations.get_automaton_name(),
        )
