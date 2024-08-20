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

from typing import List, Optional, Union
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import (
    RosField, ScxmlRosDeclarationsContainer, ScxmlExecutionBody, ScxmlSend, ScxmlTransition,
    BtGetValueInputPort, as_plain_execution_body, execution_body_from_xml, valid_execution_body)

from scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from scxml_converter.scxml_entries.ros_utils import (
    RosDeclaration, generate_srv_request_event,
    generate_srv_response_event, generate_srv_server_request_event,
    generate_srv_server_response_event, is_srv_type_known)
from scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok, get_xml_argument, read_value_from_xml_arg_or_child)
from scxml_converter.scxml_entries.utils import is_non_empty_string


class RosServiceServer(RosDeclaration):
    """Object used in SCXML root to declare a new service server."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_service_server"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosServiceServer":
        """Create a RosServiceServer object from an XML tree."""
        assert_xml_tag_ok(RosServiceServer, xml_tree)
        service_name = read_value_from_xml_arg_or_child(RosServiceServer, xml_tree, "service_name",
                                                        (BtGetValueInputPort, str))
        service_type = get_xml_argument(RosServiceServer, xml_tree, "type")
        service_alias = get_xml_argument(
            RosServiceServer, xml_tree, "name", none_allowed=True)
        return RosServiceServer(service_name, service_type, service_alias)

    def check_valid_interface_type(self) -> bool:
        if not is_srv_type_known(self._interface_type):
            print("Error: SCXML RosServiceServer: service type is not valid.")
            return False
        return True

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML RosServiceServer: invalid parameters."
        xml_srv_server = ET.Element(
            RosServiceServer.get_tag_name(),
            {"name": self._interface_alias,
             "service_name": self._interface_name, "type": self._interface_type})
        return xml_srv_server


class RosServiceClient(RosDeclaration):
    """Object used in SCXML root to declare a new service client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_service_client"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosServiceClient":
        """Create a RosServiceClient object from an XML tree."""
        assert_xml_tag_ok(RosServiceClient, xml_tree)
        service_name = read_value_from_xml_arg_or_child(RosServiceClient, xml_tree, "service_name",
                                                        (BtGetValueInputPort, str))
        service_type = get_xml_argument(RosServiceClient, xml_tree, "type")
        service_alias = get_xml_argument(
            RosServiceClient, xml_tree, "name", none_allowed=True)
        return RosServiceClient(service_name, service_type, service_alias)

    def check_valid_interface_type(self) -> bool:
        if not is_srv_type_known(self._interface_type):
            print("Error: SCXML RosServiceClient: service type is not valid.")
            return False
        return True

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML RosServiceClient: invalid parameters."
        xml_srv_server = ET.Element(
            RosServiceClient.get_tag_name(),
            {"name": self._interface_alias,
             "service_name": self._interface_name, "type": self._interface_type})
        return xml_srv_server


class RosServiceSendRequest(ScxmlSend):
    """Object representing a ROS service request (from the client side) in SCXML."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_service_send_request"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosServiceSendRequest":
        """Create a RosServiceSendRequest object from an XML tree."""
        assert_xml_tag_ok(RosServiceSendRequest, xml_tree)
        srv_name = get_xml_argument(RosServiceSendRequest, xml_tree, "name", none_allowed=True)
        if srv_name is None:
            srv_name = get_xml_argument(RosServiceSendRequest, xml_tree, "service_name")
            print("Warning: SCXML service request: 'service_name' xml arg. is deprecated. "
                  "Use 'name' instead.")
        fields: List[RosField] = []
        for field_xml in xml_tree:
            fields.append(RosField.from_xml_tree(field_xml))
        return RosServiceSendRequest(srv_name, fields)

    def __init__(self,
                 service_decl: Union[str, RosServiceClient],
                 fields: List[RosField] = None) -> None:
        """
        Initialize a new RosServiceSendRequest object.

        :param service_decl: Name of the service of Scxml obj. of Service Client declaration.
        :param fields: List of fields to be sent in the request.
        """
        if isinstance(service_decl, RosServiceClient):
            self._srv_name = service_decl.get_name()
        else:
            # Used for generating ROS entries from xml file
            assert isinstance(service_decl, str), \
                "Error: SCXML Service Send Request: invalid service name."
            self._srv_name = service_decl
        if fields is None:
            fields = []
        self._fields = fields
        assert self.check_validity(), "Error: SCXML Service Send Request: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosServiceSendRequest, "name", self._srv_name)
        valid_fields = self._fields is None or \
            all([isinstance(field, RosField) and field.check_validity() for field in self._fields])
        if not valid_fields:
            print("Error: SCXML service request: fields are not valid.")
        return valid_name and valid_fields

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ros instantiations have been declared."""
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML service request: invalid ROS declarations container."
        srv_client_declared = ros_declarations.is_service_client_defined(self._srv_name)
        if not srv_client_declared:
            print(f"Error: SCXML service request: srv client {self._srv_name} not declared.")
            return False
        valid_fields = ros_declarations.check_valid_srv_req_fields(self._srv_name, self._fields)
        if not valid_fields:
            print("Error: SCXML service request: invalid fields in request.")
            return False
        return True

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler):
        """Update the values of potential entries making use of BT ports."""
        for field in self._fields:
            field.update_bt_ports_values(bt_ports_handler)

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlSend:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML service request: invalid ROS instantiations."
        automaton_name = ros_declarations.get_automaton_name()
        srv_interface, _ = ros_declarations.get_service_client_info(self._srv_name)
        event_name = generate_srv_request_event(srv_interface, automaton_name)
        event_params = [field.as_plain_scxml(ros_declarations) for field in self._fields]
        return ScxmlSend(event_name, event_params)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Service Send Request: invalid parameters."
        xml_srv_request = ET.Element(RosServiceSendRequest.get_tag_name(),
                                     {"name": self._srv_name})
        if self._fields is not None:
            for field in self._fields:
                xml_srv_request.append(field.as_xml())
        return xml_srv_request


class RosServiceHandleRequest(ScxmlTransition):
    """SCXML object representing a ROS service callback on the server, acting upon a request."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_service_handle_request"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosServiceHandleRequest":
        """Create a RosServiceHandleRequest object from an XML tree."""
        assert_xml_tag_ok(RosServiceHandleRequest, xml_tree)
        srv_name = get_xml_argument(RosServiceHandleRequest, xml_tree, "name", none_allowed=True)
        if srv_name is None:
            srv_name = get_xml_argument(RosServiceHandleRequest, xml_tree, "service_name")
            print("Warning: SCXML service request handler: 'service_name' xml arg. is deprecated. "
                  "Use 'name' instead.")
        target_name = get_xml_argument(RosServiceHandleRequest, xml_tree, "target")
        exec_body = execution_body_from_xml(xml_tree)
        return RosServiceHandleRequest(srv_name, target_name, exec_body)

    def __init__(self, service_decl: Union[str, RosServiceServer], target: str,
                 body: Optional[ScxmlExecutionBody] = None) -> None:
        """
        Initialize a new RosServiceHandleRequest object.

        :param service_decl: The service server declaration, or its name.
        :param target: Target state after the request has been received.
        :param body: Execution body to be executed upon request, before transitioning to target.
        """
        if isinstance(service_decl, RosServiceServer):
            self._service_name = service_decl.get_name()
        else:
            # Used for generating ROS entries from xml file
            assert isinstance(service_decl, str), \
                "Error: SCXML Service Handle Request: invalid service name."
            self._service_name = service_decl
        self._target = target
        self._body = body
        assert self.check_validity(), "Error: SCXML Service Handle Request: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosServiceHandleRequest, "name", self._service_name)
        valid_target = is_non_empty_string(RosServiceHandleRequest, "target", self._target)
        valid_body = self._body is None or valid_execution_body(self._body)
        if not valid_body:
            print("Error: SCXML Service Handle Request: body is not valid.")
        return valid_name and valid_target and valid_body

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML service request handler: invalid ROS declarations container."
        srv_server_declared = ros_declarations.is_service_server_defined(self._service_name)
        if not srv_server_declared:
            print("Error: SCXML service request handler: "
                  f"srv server {self._service_name} not declared.")
            return False
        valid_body = super().check_valid_ros_instantiations(ros_declarations)
        if not valid_body:
            print("Error: SCXML service request handler: body has invalid ROS instantiations.")
        return valid_body

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlTransition:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML service request handler: invalid ROS instantiations."
        interface_name, _ = ros_declarations.get_service_server_info(self._service_name)
        event_name = generate_srv_server_request_event(interface_name)
        target = self._target
        body = as_plain_execution_body(self._body, ros_declarations)
        return ScxmlTransition(target, [event_name], None, body)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Service Handle Request: invalid parameters."
        xml_srv_request = ET.Element(RosServiceHandleRequest.get_tag_name(),
                                     {"name": self._service_name, "target": self._target})
        if self._body is not None:
            for body_elem in self._body:
                xml_srv_request.append(body_elem.as_xml())
        return xml_srv_request


class RosServiceSendResponse(ScxmlSend):
    """SCXML object representing the response from a service server."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_service_send_response"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosServiceSendResponse":
        """Create a RosServiceSendResponse object from an XML tree."""
        assert_xml_tag_ok(RosServiceSendResponse, xml_tree)
        srv_name = get_xml_argument(RosServiceSendResponse, xml_tree, "name", none_allowed=True)
        if srv_name is None:
            srv_name = get_xml_argument(RosServiceSendResponse, xml_tree, "service_name")
            print("Warning: SCXML service send response: 'service_name' xml arg. is deprecated. "
                  "Use 'name' instead.")
        fields: Optional[List[RosField]] = []
        assert fields is not None, "Error: SCXML service response: fields is not valid."
        for field_xml in xml_tree:
            fields.append(RosField.from_xml_tree(field_xml))
        if len(fields) == 0:
            fields = None
        return RosServiceSendResponse(srv_name, fields)

    def __init__(self, service_name: Union[str, RosServiceServer],
                 fields: Optional[List[RosField]]) -> None:
        """
        Initialize a new RosServiceClient object.

        :param service_name: Topic used by the service.
        :param fields: List of fields to be sent in the response.
        """
        if isinstance(service_name, RosServiceServer):
            self._service_name = service_name.get_name()
        else:
            # Used for generating ROS entries from xml file
            assert isinstance(service_name, str), \
                "Error: SCXML Service Send Response: invalid service name."
            self._service_name = service_name
        self._fields = fields if fields is not None else []
        assert self.check_validity(), "Error: SCXML Service Send Response: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosServiceSendResponse, "name", self._service_name)
        valid_fields = self._fields is None or \
            all([isinstance(field, RosField) and field.check_validity() for field in self._fields])
        if not valid_fields:
            print("Error: SCXML service response: fields are not valid.")
        return valid_name and valid_fields

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML service response: invalid ROS declarations container."
        srv_declared = ros_declarations.is_service_server_defined(self._service_name)
        if not srv_declared:
            print("Error: SCXML service response: "
                  f"srv server {self._service_name} not declared.")
            return False
        valid_fields = ros_declarations.check_valid_srv_res_fields(self._service_name, self._fields)
        if not valid_fields:
            print("Error: SCXML service response: invalid fields in response.")
            return False
        return True

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler):
        """Update the values of potential entries making use of BT ports."""
        for field in self._fields:
            field.update_bt_ports_values(bt_ports_handler)

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlSend:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML service response: invalid ROS instantiations."
        interface_name, _ = ros_declarations.get_service_server_info(self._service_name)
        event_name = generate_srv_server_response_event(interface_name)
        event_params = [field.as_plain_scxml(ros_declarations) for field in self._fields]
        return ScxmlSend(event_name, event_params)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Service Send Response: invalid parameters."
        xml_srv_response = ET.Element(RosServiceSendResponse.get_tag_name(),
                                      {"name": self._service_name})
        if self._fields is not None:
            for field in self._fields:
                xml_srv_response.append(field.as_xml())
        return xml_srv_response


class RosServiceHandleResponse(ScxmlTransition):
    """SCXML object representing the handler of a service response for a service client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_service_handle_response"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosServiceHandleResponse":
        """Create a RosServiceHandleResponse object from an XML tree."""
        assert_xml_tag_ok(RosServiceHandleResponse, xml_tree)
        srv_name = get_xml_argument(RosServiceHandleResponse, xml_tree, "name", none_allowed=True)
        if srv_name is None:
            srv_name = get_xml_argument(RosServiceHandleResponse, xml_tree, "service_name")
            print("Warning: SCXML service response handler: 'service_name' xml arg. is deprecated. "
                  "Use 'name' instead.")
        target_name = get_xml_argument(RosServiceHandleResponse, xml_tree, "target")
        exec_body = execution_body_from_xml(xml_tree)
        return RosServiceHandleResponse(srv_name, target_name, exec_body)

    def __init__(self, service_decl: Union[str, RosServiceClient], target: str,
                 body: Optional[ScxmlExecutionBody] = None) -> None:
        """
        Initialize a new RosServiceClient object.

        :param service_name: Topic used by the service.
        :param type: ROS type of the service.
        """
        if isinstance(service_decl, RosServiceClient):
            self._service_name = service_decl.get_name()
        else:
            # Used for generating ROS entries from xml file
            assert isinstance(service_decl, str), \
                "Error: SCXML Service Handle Response: invalid service name."
            self._service_name = service_decl
        self._target = target
        self._body = body
        assert self.check_validity(), "Error: SCXML Service Handle Response: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosServiceHandleResponse, "name", self._service_name)
        valid_target = is_non_empty_string(RosServiceHandleResponse, "target", self._target)
        valid_body = self._body is None or valid_execution_body(self._body)
        if not valid_body:
            print("Error: SCXML Service Handle Response: body is not valid.")
        return valid_name and valid_target and valid_body

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML Service Handle Response: invalid ROS declarations container."
        srv_declared = ros_declarations.is_service_client_defined(self._service_name)
        if not srv_declared:
            print("Error: SCXML Service Handle Response: "
                  f"srv server {self._service_name} not declared.")
            return False
        valid_body = super().check_valid_ros_instantiations(ros_declarations)
        if not valid_body:
            print("Error: SCXML Service Handle Response: body has invalid ROS instantiations.")
        return valid_body

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlTransition:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML service response handler: invalid ROS instantiations."
        automaton_name = ros_declarations.get_automaton_name()
        interface_name, _ = ros_declarations.get_service_client_info(self._service_name)
        event_name = generate_srv_response_event(interface_name, automaton_name)
        target = self._target
        body = as_plain_execution_body(self._body, ros_declarations)
        return ScxmlTransition(target, [event_name], None, body)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Service Handle Response: invalid parameters."
        xml_srv_response = ET.Element(RosServiceHandleResponse.get_tag_name(),
                                      {"name": self._service_name, "target": self._target})
        if self._body is not None:
            for body_elem in self._body:
                xml_srv_response.append(body_elem.as_xml())
        return xml_srv_response
