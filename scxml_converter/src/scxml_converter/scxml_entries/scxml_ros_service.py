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

from typing import Optional, List, Union
from scxml_converter.scxml_entries import (ScxmlBase, RosField, ScxmlSend)
from xml.etree import ElementTree as ET
from scxml_converter.scxml_entries.utils import ScxmlRosDeclarationsContainer
from scxml_converter.scxml_entries.utils import (is_srv_type_known, get_srv_type_params,
                                                 generate_srv_request_event)


class RosServiceServer(ScxmlBase):
    """Object used in SCXML root to declare a new service server."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_service_server"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosServiceServer":
        """Create a RosServiceServer object from an XML tree."""
        assert xml_tree.tag == RosServiceServer.get_tag_name(), \
            f"Error: SCXML Service Server: XML tag name is not '{RosServiceServer.get_tag_name()}'."
        service_name = xml_tree.attrib.get("service_name")
        service_type = xml_tree.attrib.get("type")
        assert service_name is not None and service_type is not None, \
            "Error: SCXML Service Server: 'service_name' or 'type' cannot be found in input xml."
        return RosServiceServer(service_name, service_type)

    def __init__(self, srv_name: str, srv_type: str) -> None:
        """
        Initialize a new RosServiceServer object.

        :param srv_name: Topic used by the service.
        :param srv_type: ROS type of the service.
        """
        self._srv_name = srv_name
        self._srv_type = srv_type

    def get_service_name(self) -> str:
        """Get the name of the service."""
        return self._srv_name

    def get_service_type(self) -> str:
        """Get the type of the service."""
        return self._srv_type

    def check_validity(self) -> bool:
        valid_name = isinstance(self._srv_name, str) and len(self._srv_name) > 0
        valid_type = is_srv_type_known(self._srv_type)
        if not valid_name:
            print("Error: SCXML Service Server: service name is not valid.")
        if not valid_type:
            print("Error: SCXML Service Server: service type is not valid.")
        return valid_name and valid_type

    def as_plain_scxml(self, _) -> ScxmlBase:
        # This is discarded in the to_plain_scxml_and_declarations method from ScxmlRoot
        raise RuntimeError("Error: SCXML ROS declarations cannot be converted to plain SCXML.")

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Service Server: invalid parameters."
        xml_srv_server = ET.Element(
            RosServiceServer.get_tag_name(),
            {"service_name": self._srv_name, "type": self._srv_type})
        return xml_srv_server


class RosServiceClient(ScxmlBase):
    """Object used in SCXML root to declare a new service client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_service_client"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosServiceClient":
        """Create a RosServiceClient object from an XML tree."""
        assert xml_tree.tag == RosServiceClient.get_tag_name(), \
            f"Error: SCXML Service Client: XML tag name is not '{RosServiceClient.get_tag_name()}'."
        service_name = xml_tree.attrib.get("service_name")
        service_type = xml_tree.attrib.get("type")
        assert service_name is not None and service_type is not None, \
            "Error: SCXML Service Client: 'service_name' or 'type' cannot be found in input xml."
        return RosServiceClient(service_name, service_type)

    def __init__(self, srv_name: str, srv_type: str) -> None:
        """
        Initialize a new RosServiceClient object.

        :param srv_name: Topic used by the service.
        :param srv_type: ROS type of the service.
        """
        self._srv_name = srv_name
        self._srv_type = srv_type

    def get_service_name(self) -> str:
        """Get the name of the service."""
        return self._srv_name

    def get_service_type(self) -> str:
        """Get the type of the service."""
        return self._srv_type

    def check_validity(self) -> bool:
        valid_name = isinstance(self._srv_name, str) and len(self._srv_name) > 0
        valid_type = is_srv_type_known(self._srv_type)
        if not valid_name:
            print("Error: SCXML Service Client: service name is not valid.")
        if not valid_type:
            print("Error: SCXML Service Client: service type is not valid.")
        return valid_name and valid_type

    def as_plain_scxml(self, _) -> ScxmlBase:
        # This is discarded in the to_plain_scxml_and_declarations method from ScxmlRoot
        raise RuntimeError("Error: SCXML ROS declarations cannot be converted to plain SCXML.")

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Service Client: invalid parameters."
        xml_srv_server = ET.Element(
            RosServiceClient.get_tag_name(),
            {"service_name": self._srv_name, "type": self._srv_type})
        return xml_srv_server


class RosServiceSendRequest(ScxmlBase):
    """Object representing a ROS service request (from the client side) in SCXML."""

    def __init__(self,
                 service_decl: Union[str, RosServiceClient],
                 fields: Optional[List[RosField]]) -> None:
        """
        Initialize a new RosServiceClient object.

        :param service_decl: Name of the service of Scxml obj. of Service Client declaration.
        :param type: List of fields to be sent in the request.
        """
        if isinstance(service_decl, RosServiceClient):
            self._srv_name = service_decl.get_service_name()
        else:
            # Used for generating ROS entries from xml file
            assert isinstance(service_decl, str), \
                "Error: SCXML Service Send Request: invalid service name."
            self._srv_name = service_decl
        self._fields = fields
        assert self.check_validity(), "Error: SCXML Service Send Request: invalid parameters."

    def get_tag_name() -> str:
        return "ros_service_send_request"

    def from_xml_tree(xml_tree: ET.Element) -> "RosServiceSendRequest":
        """Create a RosServiceServer object from an XML tree."""
        assert xml_tree.tag == RosServiceSendRequest.get_tag_name(), \
            "Error: SCXML service request: XML tag name is not " + \
            RosServiceSendRequest.get_tag_name()
        srv_name = xml_tree.attrib.get("service_name")
        assert srv_name is not None, \
            "Error: SCXML service request: 'service_name' attribute not found in input xml."
        fields = []
        for field_xml in xml_tree:
            fields.append(RosField.from_xml_tree(field_xml))
        if len(fields) == 0:
            fields = None
        return RosServiceSendRequest(srv_name, fields)

    def check_validity(self) -> bool:
        valid_name = isinstance(self._srv_name, str) and len(self._srv_name) > 0
        valid_fields = self._fields is None or \
            all([isinstance(field, RosField) for field in self._fields])
        if not valid_name:
            print("Error: SCXML service request: service name is not valid.")
        if not valid_fields:
            print("Error: SCXML service request: fields are not valid.")
        return valid_name and valid_fields

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlSend:
        service_type = ros_declarations.get_service_client_type(self._srv_name)
        expected_params, _ = get_srv_type_params(service_type)
        event_name = generate_srv_request_event(
            self._srv_name, ros_declarations.get_automaton_name())
        for field in self._fields:
            assert field.get_name() in expected_params, \
                f"Error: SCXML service request: field {field.get_name()} not in {service_type}."
            expected_params.pop(field.get_name())
        assert len(expected_params) == 0, \
            f"Error: SCXML service request: missing fields {expected_params}."
        event_params = [field.as_plain_scxml() for field in self._fields]
        return ScxmlSend(event_name, event_params)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Service Send Request: invalid parameters."
        xml_srv_request = ET.Element(RosServiceSendRequest.get_tag_name(),
                                     {"service_name": self._srv_name})
        if self._fields is not None:
            for field in self._fields:
                xml_srv_request.append(field.as_xml())
        return xml_srv_request


class RosServiceHandleRequest(ScxmlBase):
    """SCXML object representing a ROS service callback on the server, acting upon a request."""

    def __init__(self, service_name: str, target: str) -> None:
        """
        Initialize a new RosServiceClient object.

        :param service_name: Topic used by the service.
        :param type: ROS type of the service.
        """
        self._service_name = service_name
        self._type = type

    def get_tag_name() -> str:
        return "ros_service_handle_request"

    def from_xml_tree(xml_tree: ET.Element) -> "RosServiceClient":
        """Create a RosServiceServer object from an XML tree."""
        pass

    def check_validity(self) -> bool:
        pass

    def as_plain_scxml(self, _) -> ScxmlBase:
        pass

    def as_xml(self) -> ET.Element:
        pass


class RosServiceSendResponse(ScxmlBase):
    """Object used in SCXML root to declare a new service client."""

    def __init__(self, service_name: str, type: str) -> None:
        """
        Initialize a new RosServiceClient object.

        :param service_name: Topic used by the service.
        :param type: ROS type of the service.
        """
        self._service_name = service_name
        self._type = type

    def get_tag_name() -> str:
        return "ros_service_send_response"

    def from_xml_tree(xml_tree: ET.Element) -> "RosServiceClient":
        """Create a RosServiceServer object from an XML tree."""
        pass

    def check_validity(self) -> bool:
        pass

    def as_plain_scxml(self, _) -> ScxmlBase:
        pass

    def as_xml(self) -> ET.Element:
        pass


class RosServiceHandleResponse(ScxmlBase):
    """Object used in SCXML root to declare a new service client."""

    def __init__(self, service_name: str, type: str) -> None:
        """
        Initialize a new RosServiceClient object.

        :param service_name: Topic used by the service.
        :param type: ROS type of the service.
        """
        self._service_name = service_name
        self._type = type

    def get_tag_name() -> str:
        return "ros_service_handle_response"

    def from_xml_tree(xml_tree: ET.Element) -> "RosServiceClient":
        """Create a RosServiceServer object from an XML tree."""
        pass

    def check_validity(self) -> bool:
        pass

    def as_plain_scxml(self, _) -> ScxmlBase:
        pass

    def as_xml(self) -> ET.Element:
        pass
