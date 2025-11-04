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

from typing import Callable, Dict, List, Tuple

from moco.roaml_generator.ros_helpers.ros_communication_handler import RosCommunicationHandler
from moco.roaml_converter.scxml_entries import (
    ScxmlAssign,
    ScxmlData,
    ScxmlDataModel,
    ScxmlIf,
    ScxmlParam,
    ScxmlRoot,
    ScxmlSend,
    ScxmlState,
    ScxmlTransition,
)
from moco.roaml_converter.scxml_entries.ros_utils import (
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
    get_action_goal_id_definition,
    get_action_type_params,
    sanitize_ros_interface_name,
)
from moco.roaml_converter.scxml_entries.utils import (
    PLAIN_FIELD_EVENT_PREFIX,
    PLAIN_SCXML_EVENT_DATA_PREFIX,
    ROS_FIELD_PREFIX,
)


class RosActionHandler(RosCommunicationHandler):
    """
    Object storing the declarations related to a ROS Action and creating an handler for them.
    """

    @staticmethod
    def get_interface_prefix() -> str:
        return "action_handler_"

    def _generate_goal_request_transition(
        self, goal_state: ScxmlState, client_id: str, goal_id: int, req_params: Dict[str, str]
    ) -> ScxmlTransition:
        """
        Generate a scxml transition that, given a client request, sends an event to the server.

        :param client_id: Id of the client that sent the request.
        :param goal_id: Id of the goal associated with the client.
        :param req_params: Dictionary of the parameters of the request.
        """
        goal_id_name = get_action_goal_id_definition()[0]
        action_client_req_event = generate_action_goal_req_event(self._interface_name, client_id)
        action_srv_handle_event = generate_action_goal_handle_event(self._interface_name)
        goal_req_transition = ScxmlTransition.make_single_target_transition(
            goal_state.get_id(), [action_client_req_event]
        )
        send_params = [ScxmlParam(goal_id_name, expr=str(goal_id))]
        for field_name in req_params:
            # Add preliminary assignments (part of the hack mentioned in self.to_scxml())
            field_w_pref = ROS_FIELD_PREFIX + field_name
            goal_req_transition.append_body_executable_entry(
                ScxmlAssign(field_w_pref, PLAIN_FIELD_EVENT_PREFIX + field_name)
            )
            send_params.append(ScxmlParam(field_w_pref, expr=field_w_pref))
        # Add the send to the server
        goal_req_transition.append_body_executable_entry(
            ScxmlSend(action_srv_handle_event, send_params)
        )
        return goal_req_transition

    def _generate_srv_event_transition(
        self,
        goal_state: ScxmlState,
        client_to_goal_id: List[Tuple[str, int]],
        event_fields: Dict[str, str],
        srv_event_function: Callable[[str], str],
        client_event_function: Callable[[str, str], str],
        additional_data: List[str],
    ) -> ScxmlTransition:
        """
        Generate a scxml transition that triggers the client related to the input event's goal_id.

        :param client_to_goal_id: List of tuples (client_id, goal_id) relating clients to goal ids.
        :param event_fields: Dictionary of the parameters of the event.
        :param srv_event_function: Function to generate the server (input) event name.
        :param client_event_function: Function to generate the client (output) event name.
        :param additional_fields: List of additional fields to be added to the event.
        """
        goal_id_name = get_action_goal_id_definition()[0]
        extra_entries = additional_data + [goal_id_name]
        srv_event_name = srv_event_function(self._interface_name)
        scxml_transition = ScxmlTransition.make_single_target_transition(
            goal_state.get_id(), [srv_event_name]
        )
        for entry_name in extra_entries:
            scxml_transition.append_body_executable_entry(
                ScxmlAssign(entry_name, PLAIN_SCXML_EVENT_DATA_PREFIX + entry_name)
            )
        out_params: List[ScxmlParam] = []
        for entry_name in additional_data:
            out_params.append(ScxmlParam(entry_name, expr=entry_name))
        for field_name in event_fields:
            field_w_pref = ROS_FIELD_PREFIX + field_name
            scxml_transition.append_body_executable_entry(
                ScxmlAssign(field_w_pref, PLAIN_FIELD_EVENT_PREFIX + field_name)
            )
            out_params.append(ScxmlParam(field_w_pref, expr=field_w_pref))
        condition_send_pairs: List[Tuple[str, List[ScxmlSend]]] = []
        for client_id, goal_id in client_to_goal_id:
            client_event = client_event_function(self._interface_name, client_id)
            condition_send_pairs.append(
                (f"{goal_id_name} == {goal_id}", [ScxmlSend(client_event, out_params)])
            )
        scxml_transition.append_body_executable_entry(ScxmlIf(condition_send_pairs))
        return scxml_transition

    def _generate_goal_accept_transition(
        self, goal_state: ScxmlState, client_to_goal_id: List[Tuple[str, int]]
    ) -> ScxmlTransition:
        """
        Generate a scxml transition that sends an event to the client to report an accepted goal.

        :param client_to_goal_id: List of tuples (client_id, goal_id) relating clients to goal ids.
        """
        return self._generate_srv_event_transition(
            goal_state,
            client_to_goal_id,
            {},
            generate_action_goal_accepted_event,
            generate_action_goal_handle_accepted_event,
            [],
        )

    def _generate_goal_reject_transition(
        self, goal_state: ScxmlState, client_to_goal_id: List[Tuple[str, int]]
    ) -> ScxmlTransition:
        """
        Generate a scxml transition that sends an event to the client to report a rejected goal.

        :param client_to_goal_id: List of tuples (client_id, goal_id) relating clients to goal ids.
        """
        return self._generate_srv_event_transition(
            goal_state,
            client_to_goal_id,
            {},
            generate_action_goal_rejected_event,
            generate_action_goal_handle_rejected_event,
            [],
        )

    def _generate_feedback_response_transition(
        self,
        goal_state: ScxmlState,
        client_to_goal_id: List[Tuple[str, int]],
        feedback_params: Dict[str, str],
    ) -> ScxmlTransition:
        """
        Generate a scxml transition that sends an event to the client to report feedback.

        :param client_to_goal_id: List of tuples (client_id, goal_id) relating clients to goal ids.
        :param feedback_params: Dictionary of the parameters of the feedback.
        """
        return self._generate_srv_event_transition(
            goal_state,
            client_to_goal_id,
            feedback_params,
            generate_action_feedback_event,
            generate_action_feedback_handle_event,
            [],
        )

    def _generate_result_response_transition(
        self,
        goal_state: ScxmlState,
        client_to_goal_id: List[Tuple[str, int]],
        result_params: Dict[str, str],
    ) -> ScxmlTransition:
        """
        Generate a scxml transition that sends an event to the client to report the result.

        :param client_to_goal_id: List of tuples (client_id, goal_id) relating clients to goal ids.
        :param result_params: Dictionary of the parameters of the result.
        """
        return self._generate_srv_event_transition(
            goal_state,
            client_to_goal_id,
            result_params,
            generate_action_result_event,
            generate_action_result_handle_event,
            ["code"],
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

        # Design choice: we generate a unique goal_id for each client, and we use it to identify
        # the recipient of the response.
        client_to_goal_id: List[Tuple[str, int]] = [
            (client_id, goal_id) for goal_id, client_id in enumerate(self._clients_automata)
        ]

        goal_params, feedback_params, result_params = get_action_type_params(self._interface_type)

        # Hack: Using support variables in the data model to avoid having _event in send params
        goal_id_def = get_action_goal_id_definition()
        action_fields_as_data = self._generate_datamodel_from_ros_fields(
            goal_params | feedback_params | result_params
        )
        action_fields_as_data.append(ScxmlData(goal_id_def[0], "0", goal_id_def[1]))
        action_fields_as_data.append(ScxmlData("code", "0", "int32"))
        # Make sure the service name has no slashes and spaces
        scxml_root_name = self.get_interface_prefix() + sanitize_ros_interface_name(
            self._interface_name
        )
        wait_state = ScxmlState("waiting")
        goal_requested_state = ScxmlState("goal_requested")
        for client_id, goal_id in client_to_goal_id:
            wait_state.add_transition(
                self._generate_goal_request_transition(
                    goal_requested_state, client_id, goal_id, goal_params
                )
            )
        goal_requested_state.add_transition(
            self._generate_goal_accept_transition(wait_state, client_to_goal_id)
        )
        goal_requested_state.add_transition(
            self._generate_goal_reject_transition(wait_state, client_to_goal_id)
        )
        wait_state.add_transition(
            self._generate_feedback_response_transition(
                wait_state, client_to_goal_id, feedback_params
            )
        )
        wait_state.add_transition(
            self._generate_result_response_transition(wait_state, client_to_goal_id, result_params)
        )
        scxml_root = ScxmlRoot(scxml_root_name)
        scxml_root.set_data_model(ScxmlDataModel(action_fields_as_data))
        scxml_root.add_state(wait_state, initial=True)
        scxml_root.add_state(goal_requested_state)
        assert scxml_root.is_plain_scxml(), "Generated SCXML for srv sync is not plain SCXML."
        return scxml_root
