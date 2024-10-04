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
Representation of ROS Services.
"""

from typing import Dict, List

from as2fm.as2fm_common.logging import AS2FMLogger
from as2fm.jani_generator.ros_helpers.ros_communication_handler import RosCommunicationHandler
from as2fm.scxml_converter.scxml_entries import (
    ScxmlAssign,
    ScxmlDataModel,
    ScxmlParam,
    ScxmlRoot,
    ScxmlSend,
    ScxmlState,
    ScxmlTransition,
)
from as2fm.scxml_converter.scxml_entries.ros_utils import (
    generate_srv_request_event,
    generate_srv_response_event,
    generate_srv_server_request_event,
    generate_srv_server_response_event,
    get_srv_type_params,
    sanitize_ros_interface_name,
)
from as2fm.scxml_converter.scxml_entries.utils import PLAIN_FIELD_EVENT_PREFIX, ROS_FIELD_PREFIX


class RosServiceHandler(RosCommunicationHandler):
    """
    Object storing the declarations related to a ROS Service and creating an handler for them.
    """

    @staticmethod
    def get_interface_prefix() -> str:
        return "srv_handler_"

    def generate_transition_to_processing_state(
        self, client_id: str, req_fields: Dict[str, str]
    ) -> ScxmlTransition:
        """
        Generate a transition from the waiting state to the processing state for a given client.

        :param client_id: The id of the client to generate the transition for.
        :param req_fields: The fields of the request to be assigned to the data model.
        :return: The generated transition.
        """
        assignments: List[ScxmlAssign] = []
        event_params: List[ScxmlParam] = []
        for field_name in req_fields:
            field_w_pref = ROS_FIELD_PREFIX + field_name
            assignments.append(ScxmlAssign(field_w_pref, PLAIN_FIELD_EVENT_PREFIX + field_name))
            event_params.append(ScxmlParam(field_w_pref, expr=field_w_pref))
        return ScxmlTransition(
            f"processing_client_{client_id}",
            [generate_srv_request_event(self._interface_name, client_id)],
            body=assignments
            + [
                ScxmlSend(
                    generate_srv_server_request_event(self._interface_name),
                    event_params,
                )
            ],
        )

    def generate_transition_from_processing_state(
        self, client_id: str, res_fields: Dict[str, str]
    ) -> ScxmlTransition:
        """
        Generate a transition from the processing state to the waiting state for a given client.
        """
        assignments: List[ScxmlAssign] = []
        event_params: List[ScxmlParam] = []
        for field_name in res_fields:
            field_w_pref = ROS_FIELD_PREFIX + field_name
            assignments.append(ScxmlAssign(field_w_pref, PLAIN_FIELD_EVENT_PREFIX + field_name))
            event_params.append(ScxmlParam(field_w_pref, expr=field_w_pref))
        return ScxmlTransition(
            "waiting",
            [generate_srv_server_response_event(self._interface_name)],
            body=assignments
            + [
                ScxmlSend(
                    generate_srv_response_event(self._interface_name, client_id),
                    event_params,
                )
            ],
        )

    def to_scxml(self) -> ScxmlRoot:
        """
        Generate the srv_handler automaton that implements the link between the server of this
        service and its clients.
        This ensures that only one request can be processed at the time and that the client receives
        only the response related to it's request.

        :return: Scxml object representing the necessary file content.
        """
        self._assert_validity()
        req_params, res_params = get_srv_type_params(self._interface_type)
        # Hack: Using support variables in the data model to avoid having _event in send params
        req_fields_as_data = self._generate_datamodel_from_ros_fields(req_params | res_params)
        # Make sure the service name has no slashes and spaces
        scxml_root_name = self.get_interface_prefix() + sanitize_ros_interface_name(
            self._interface_name
        )
        wait_state = ScxmlState(
            "waiting",
            body=[
                self.generate_transition_to_processing_state(client_id, req_params)
                for client_id in self._clients_automata
            ],
        )
        processing_states = [
            ScxmlState(
                f"processing_client_{client_id}",
                body=[self.generate_transition_from_processing_state(client_id, res_params)],
            )
            for client_id in self._clients_automata
        ]
        # Prepare the ScxmlRoot object and return it
        scxml_root = ScxmlRoot(scxml_root_name, AS2FMLogger())
        scxml_root.set_data_model(ScxmlDataModel(req_fields_as_data))
        scxml_root.add_state(wait_state, initial=True)
        for processing_state in processing_states:
            scxml_root.add_state(processing_state)
        assert scxml_root.is_plain_scxml(), "Generated SCXML for srv sync is not plain SCXML."
        return scxml_root
