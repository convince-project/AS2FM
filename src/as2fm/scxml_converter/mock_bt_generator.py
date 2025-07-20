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
Generate mock BT plugins for thorough BT verification.
"""

import os
import random
from typing import Dict, List, Optional

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.scxml_converter.bt_converter import (
    generate_bt_children_scxmls,
    generate_bt_root_scxml,
)
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import (
    ScxmlAssign,
    ScxmlData,
    ScxmlDataModel,
    ScxmlRoot,
    ScxmlState,
    ScxmlTransition,
)
from as2fm.scxml_converter.scxml_entries.scxml_bt_comm_interfaces import (
    BtHalt,
    BtReturnHalted,
    BtReturnTickStatus,
    BtTick,
)
from as2fm.scxml_converter.scxml_entries.scxml_transition_target import ScxmlTransitionTarget


class MockBtPluginGenerator:
    """Generator for mock BT plugins that randomly return different states."""

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the mock generator.

        :param seed: Random seed for reproducible behavior
        """
        self.seed = seed
        if seed is not None:
            random.seed(seed)

    def generate_mock_condition_plugin(self, condition_id: str) -> ScxmlRoot:
        """
        Generate a mock condition plugin that randomly returns SUCCESS or FAILURE.

        :param condition_id: The ID of the condition node
        :return: SCXML root for the mock condition
        """
        scxml_name = f"MockCondition_{condition_id}"
        scxml_root = ScxmlRoot(scxml_name)

        # Data model for tracking execution
        data_model = ScxmlDataModel(
            [
                ScxmlData("execution_count", "0", "int32"),
                ScxmlData("last_result", "'SUCCESS'", "string"),
                ScxmlData("success_probability", "0.5", "float32"),
            ]
        )
        scxml_root.set_data_model(data_model)

        # Initial state
        init_state = ScxmlState("init")
        init_state.add_transition(ScxmlTransition.make_single_target_transition("idle", []))
        scxml_root.add_state(init_state, initial=True)

        # Idle state - responds to BT ticks
        idle_state = ScxmlState("idle")

        # BT tick transition - use probabilistic transitions instead of random expressions
        # Create transition targets with probabilities
        success_target = ScxmlTransitionTarget(
            "return_success",
            probability=0.5,  # Will be replaced with success_probability during conversion
            body=[
                ScxmlAssign("execution_count", "execution_count + 1"),
                ScxmlAssign("last_result", "'SUCCESS'"),
            ],
        )

        failure_target = ScxmlTransitionTarget(
            "return_failure",
            probability=0.5,  # Will be replaced with 1 - success_probability during conversion
            body=[
                ScxmlAssign("execution_count", "execution_count + 1"),
                ScxmlAssign("last_result", "'FAILURE'"),
            ],
        )

        # Create transition with multiple probabilistic targets
        tick_transition = BtTick([success_target, failure_target])
        idle_state.add_transition(tick_transition)

        # Add return states
        return_success_state = ScxmlState("return_success")
        return_success_state.add_transition(
            ScxmlTransition.make_single_target_transition(
                "idle", body=[BtReturnTickStatus("SUCCESS")]
            )
        )
        scxml_root.add_state(return_success_state)

        return_failure_state = ScxmlState("return_failure")
        return_failure_state.add_transition(
            ScxmlTransition.make_single_target_transition(
                "idle", body=[BtReturnTickStatus("FAILURE")]
            )
        )
        scxml_root.add_state(return_failure_state)

        # BT halt transition
        halt_transition = BtHalt.make_single_target_transition("idle", body=[BtReturnHalted()])
        idle_state.add_transition(halt_transition)

        scxml_root.add_state(idle_state)

        return scxml_root

    def generate_mock_action_plugin(self, action_id: str) -> ScxmlRoot:
        """
        Generate a mock action plugin that can return SUCCESS, FAILURE, or RUNNING.

        :param action_id: The ID of the action node
        :return: SCXML root for the mock action
        """
        scxml_name = f"MockAction_{action_id}"
        scxml_root = ScxmlRoot(scxml_name)

        # Data model for tracking execution
        data_model = ScxmlDataModel(
            [
                ScxmlData("execution_count", "0", "int32"),
                ScxmlData("last_result", "'SUCCESS'", "string"),
                ScxmlData("success_probability", "0.6", "float32"),
                ScxmlData("running_probability", "0.2", "float32"),
                ScxmlData("ticks_in_running", "0", "int32"),
                ScxmlData("max_running_ticks", "5", "int32"),
            ]
        )
        scxml_root.set_data_model(data_model)

        # Initial state
        init_state = ScxmlState("init")
        init_state.add_transition(ScxmlTransition.make_single_target_transition("idle", []))
        scxml_root.add_state(init_state, initial=True)

        # Idle state - responds to BT ticks
        idle_state = ScxmlState("idle")

        # BT tick transition - use probabilistic transitions for SUCCESS, FAILURE, RUNNING
        # Create transition targets with probabilities
        success_target = ScxmlTransitionTarget(
            "return_success",
            probability=0.6,  # Will be replaced with success_probability during conversion
            body=[
                ScxmlAssign("execution_count", "execution_count + 1"),
                ScxmlAssign("last_result", "'SUCCESS'"),
            ],
        )

        running_target = ScxmlTransitionTarget(
            "return_running",
            probability=0.2,  # Will be replaced with running_probability during conversion
            body=[
                ScxmlAssign("execution_count", "execution_count + 1"),
                ScxmlAssign("last_result", "'RUNNING'"),
                ScxmlAssign("ticks_in_running", "1"),
            ],
        )

        failure_target = ScxmlTransitionTarget(
            "return_failure",
            probability=0.2,  # Will be replaced with 1 - success_probability - running_probability during conversion # noqa: E501
            body=[
                ScxmlAssign("execution_count", "execution_count + 1"),
                ScxmlAssign("last_result", "'FAILURE'"),
            ],
        )

        # Create transition with multiple probabilistic targets
        tick_transition = BtTick([success_target, running_target, failure_target])
        idle_state.add_transition(tick_transition)

        # Add return states
        return_success_state = ScxmlState("return_success")
        return_success_state.add_transition(
            ScxmlTransition.make_single_target_transition(
                "idle", body=[BtReturnTickStatus("SUCCESS")]
            )
        )
        scxml_root.add_state(return_success_state)

        return_failure_state = ScxmlState("return_failure")
        return_failure_state.add_transition(
            ScxmlTransition.make_single_target_transition(
                "idle", body=[BtReturnTickStatus("FAILURE")]
            )
        )
        scxml_root.add_state(return_failure_state)

        return_running_state = ScxmlState("return_running")
        return_running_state.add_transition(
            ScxmlTransition.make_single_target_transition(
                "idle", body=[BtReturnTickStatus("RUNNING")]
            )
        )
        scxml_root.add_state(return_running_state)

        # BT halt transition
        halt_transition = BtHalt.make_single_target_transition(
            "idle", body=[ScxmlAssign("ticks_in_running", "0"), BtReturnHalted()]
        )
        idle_state.add_transition(halt_transition)

        scxml_root.add_state(idle_state)

        return scxml_root

    def generate_mock_plugins_from_bt_xml(self, bt_xml_path: str) -> Dict[str, ScxmlRoot]:
        """
        Generate mock plugins for all conditions and actions found in a BT XML file.

        :param bt_xml_path: Path to the BT XML file
        :return: Dictionary mapping node IDs to mock SCXML plugins
        """
        mock_plugins = {}

        # Parse BT XML
        xml_tree = ET.parse(bt_xml_path, ET.XMLParser(remove_comments=True)).getroot()

        # Find all Condition and Action nodes
        for element in xml_tree.iter():
            if element.tag == "Condition" and "ID" in element.attrib:
                condition_id = element.attrib["ID"]
                mock_plugins[condition_id] = self.generate_mock_condition_plugin(condition_id)
            elif element.tag == "Action" and "ID" in element.attrib:
                action_id = element.attrib["ID"]
                mock_plugins[action_id] = self.generate_mock_action_plugin(action_id)

        return mock_plugins


def _get_bt_children_from_xml(bt_xml_path: str) -> List[XmlElement]:
    """
    Extract BT children from XML file.

    :param bt_xml_path: Path to the BT XML file
    :return: List of BT child elements
    """
    xml_tree: XmlElement = ET.parse(bt_xml_path, ET.XMLParser(remove_comments=True)).getroot()
    root_children = xml_tree.getchildren()
    assert len(root_children) == 1, f"Error: Expected one root element, found {len(root_children)}."
    assert (
        root_children[0].tag == "BehaviorTree"
    ), f"Error: Expected BehaviorTree root, found {root_children[0].tag}."
    bt_children = root_children[0].getchildren()
    assert (
        len(bt_children) == 1
    ), f"Error: Expected one BehaviorTree child, found {len(bt_children)}."
    return bt_children


def create_mock_bt_converter(
    bt_xml_path: str,
    bt_tick_rate: float,
    tick_if_not_running: bool,
    custom_data_types: Dict[str, StructDefinition],
    seed: Optional[int] = None,
) -> List[ScxmlRoot]:
    """
    Create a BT converter that uses mock plugins instead of real ones.

    :param bt_xml_path: Path to the BT XML file
    :param bt_tick_rate: The rate at which the BT root is ticked
    :param tick_if_not_running: If true, keep ticking after BT stops returning RUNNING
    :param custom_data_types: Custom data type definitions
    :param seed: Random seed for reproducible mock behavior
    :return: List of generated SCXML models
    """
    from importlib.resources import files as resource_files

    # Generate mock plugins
    mock_generator = MockBtPluginGenerator(seed)
    mock_plugins = mock_generator.generate_mock_plugins_from_bt_xml(bt_xml_path)

    # Create available plugins dictionary with mock plugins and control nodes
    available_bt_plugins = {}

    # Add mock plugins
    for node_id, mock_plugin in mock_plugins.items():
        available_bt_plugins[node_id] = mock_plugin

    # Add control nodes
    internal_bt_plugins_path = (
        resource_files("as2fm").joinpath("resources").joinpath("bt_control_nodes")
    )
    for plugin_path in internal_bt_plugins_path.iterdir():
        if plugin_path.is_file() and plugin_path.suffix == ".scxml":
            bt_plugin_scxml = ScxmlRoot.from_scxml_file(str(plugin_path), custom_data_types)
            available_bt_plugins[bt_plugin_scxml.get_name()] = bt_plugin_scxml

    # Get BT structure
    bt_children = _get_bt_children_from_xml(bt_xml_path)
    root_child_tick_idx = 1000
    bt_name = f"mock_{os.path.basename(bt_xml_path).replace('.xml', '')}"

    # Generate BT root
    bt_scxml_root = generate_bt_root_scxml(
        bt_name, root_child_tick_idx, bt_tick_rate, tick_if_not_running
    )
    bt_scxml_root.set_custom_data_types({})

    # Generate child SCXMLs using available plugins
    generated_scxmls = [bt_scxml_root] + generate_bt_children_scxmls(
        bt_children[0], root_child_tick_idx, available_bt_plugins
    )

    return generated_scxmls
