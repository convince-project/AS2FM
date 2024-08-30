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
Helper to create an orchestrator out of ROS Actions declarations.
"""

from typing import Dict, List, Tuple

from jani_generator.ros_helpers.ros_communication_handler import RosCommunicationHandler

from scxml_converter.scxml_entries import (
    ScxmlAssign, ScxmlDataModel, ScxmlParam, ScxmlRoot, ScxmlSend, ScxmlState, ScxmlTransition)
from scxml_converter.scxml_entries.ros_utils import (
    get_action_type_params,
    generate_action_goal_handle_event, generate_action_goal_req_event,
    get_action_goal_id_definition,
    sanitize_ros_interface_name)


class RosActionHandler(RosCommunicationHandler):
    """
    Object storing the declarations related to a ROS Action and creating an handler for them.
    """

    @staticmethod
    def get_interface_prefix() -> str:
        return "action_handler_"

    def _generate_goal_request_transition(
            self, client_id: str, goal_id: int, req_params: Dict[str, str]) -> ScxmlTransition:
        action_client_req_event = generate_action_goal_req_event(self._interface_name, client_id)
        action_srv_handle_event = generate_action_goal_handle_event(self._interface_name)
        goal_req_transition = ScxmlTransition("waiting", [action_client_req_event])
        send_params = [ScxmlParam("goal_id", str(goal_id))]
        for field_name in req_params:
            # Add preliminary assignments (part of the hack mentioned in self.to_scxml())
            goal_req_transition.append_body_executable_entry(
                ScxmlAssign(field_name, f"_event.{field_name}"))
            send_params.append(ScxmlParam(field_name, field_name))
        # Add the send to the server
        goal_req_transition.append_body_executable_entry(
            ScxmlSend(action_srv_handle_event, send_params))
        return goal_req_transition

    def _generate_goal_accept_transition(
            self, client_to_goal_id: List[Tuple[str, int]]) -> ScxmlTransition:
        pass

    def _generate_goal_reject_transition(
            self, client_to_goal_id: List[Tuple[str, int]]) -> ScxmlTransition:
        pass

    def _generate_feedback_response_transition(
            self, client_to_goal_id: List[Tuple[str, int]], feedback_params: Dict[str, str]
            ) -> ScxmlTransition:
        pass

    def _generate_result_response_transition(
            self, client_to_goal_id: List[Tuple[str, int]], result_params: Dict[str, str]
            ) -> ScxmlTransition:
        pass

    def to_scxml(self) -> ScxmlRoot:
        """
        Generate the srv_handler automaton that implements the link between the server of this
        service and its clients.
        This ensures that only one request can be processed at the time and that the client receives
        only the response related to it's request.

        :return: Scxml object representing the necessary file content.
        """
        self._assert_validity()

        # Design choice: we generate a unique goal_id for each client, and we use it to identify
        # the recipient of the response.
        client_to_goal_id: List[Tuple[str, int]] = [
            (client_id, goal_id) for goal_id, client_id in enumerate(self._clients_automata)]

        goal_params, feedback_params, result_params = get_action_type_params(self._interface_type)

        # Hack: Using support variables in the data model to avoid having _event in send params
        goal_id_def = get_action_goal_id_definition()
        req_fields_as_data = self._generate_datamodel_from_ros_fields(
            goal_params | feedback_params | result_params | {goal_id_def[0]: goal_id_def[1]})
        # Make sure the service name has no slashes and spaces
        scxml_root_name = \
            self.get_interface_prefix() + sanitize_ros_interface_name(self._interface_name)
        wait_state = ScxmlState("waiting")
        for client_id, goal_id in client_to_goal_id:
            wait_state.add_transition(
                self._generate_goal_request_transition(client_id, goal_id, goal_params))
        wait_state.add_transition(self._generate_goal_accept_transition(client_to_goal_id))
        wait_state.add_transition(self._generate_goal_reject_transition(client_to_goal_id))
        wait_state.add_transition(self._generate_feedback_response_transition(
            client_to_goal_id, feedback_params))
        wait_state.add_transition(self._generate_result_response_transition(
            client_to_goal_id, result_params))
        scxml_root = ScxmlRoot(scxml_root_name)
        scxml_root.set_data_model(ScxmlDataModel(req_fields_as_data))
        scxml_root.add_state(wait_state, initial=True)
        assert scxml_root.is_plain_scxml(), "Generated SCXML for srv sync is not plain SCXML."
        return scxml_root


# Mapping from Ros Action name and their handler instance
RosActions = Dict[str, RosActionHandler]
