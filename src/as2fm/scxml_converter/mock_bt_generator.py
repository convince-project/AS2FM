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
Generate mock BT plugins using SCXML templates for better readability and maintainability.
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
from as2fm.scxml_converter.scxml_entries import ScxmlRoot, load_scxml_file


class MockBtPluginGenerator:
    """Generator for mock BT plugins using SCXML templates."""

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the mock generator.

        :param seed: Random seed for reproducible behavior
        """
        self.seed = seed
        if seed is not None:
            random.seed(seed)

    def _load_scxml_template(self, template_name: str) -> str:
        """
        Load SCXML template content from resources.

        :param template_name: Name of the template file (without .scxml extension)
        :return: SCXML template content as string
        """
        from importlib.resources import files as resource_files

        template_path = (
            resource_files("as2fm")
            .joinpath("resources")
            .joinpath("mock_bt_nodes")
            .joinpath(f"{template_name}.scxml")
        )

        return template_path.read_text(encoding="utf-8")

    def _customize_scxml_template(
        self,
        template_content: str,
        node_id: str,
        node_type: str,
        success_probability: float = None,
        running_probability: float = None,
    ) -> str:
        """
        Customize SCXML template with specific node parameters.

        :param template_content: The SCXML template content
        :param node_id: The ID of the BT node
        :param node_type: Type of node (condition or action)
        :param success_probability: Success probability for the node
        :param running_probability: Running probability for action nodes
        :return: Customized SCXML content
        """
        # Replace template name with actual node ID
        customized_content = template_content.replace(
            f"Mock{node_type.capitalize()}_TEMPLATE", f"Mock{node_type.capitalize()}_{node_id}"
        )

        # Set success probability if provided
        if success_probability is not None:
            customized_content = customized_content.replace(
                'expr="0.5"', f'expr="{success_probability}"'
            )

        # Set running probability for action nodes if provided
        if running_probability is not None and node_type == "action":
            customized_content = customized_content.replace(
                'expr="0.2"', f'expr="{running_probability}"'
            )

        return customized_content

    def generate_mock_condition_plugin(
        self, condition_id: str, success_probability: float = 0.5
    ) -> ScxmlRoot:
        """
        Generate a mock condition plugin using SCXML template.

        :param condition_id: The ID of the condition node
        :param success_probability: Probability of returning SUCCESS (default: 0.5)
        :return: SCXML root for the mock condition
        """
        # Load template
        template_content = self._load_scxml_template("mock_condition")

        # Customize template
        customized_content = self._customize_scxml_template(
            template_content, condition_id, "condition", success_probability=success_probability
        )

        # Parse and create ScxmlRoot
        xml_element = ET.fromstring(customized_content.encode("utf-8"))

        # Remove namespaces from all elements (required by SCXML parser)
        from as2fm.as2fm_common.common import remove_namespace

        for child in xml_element.iter():
            child.tag = remove_namespace(child.tag)

        # Set file path attribute for proper error reporting
        from as2fm.as2fm_common.logging import set_filepath_for_all_sub_elements

        set_filepath_for_all_sub_elements(xml_element, f"mock_condition_{condition_id}.scxml")

        return ScxmlRoot.from_xml_tree(xml_element, {})

    def generate_mock_action_plugin(
        self, action_id: str, success_probability: float = 0.6, running_probability: float = 0.2
    ) -> ScxmlRoot:
        """
        Generate a mock action plugin using SCXML template.

        :param action_id: The ID of the action node
        :param success_probability: Probability of returning SUCCESS (default: 0.6)
        :param running_probability: Probability of returning RUNNING (default: 0.2)
        :return: SCXML root for the mock action
        """
        # Load template
        template_content = self._load_scxml_template("mock_action")

        # Customize template
        customized_content = self._customize_scxml_template(
            template_content,
            action_id,
            "action",
            success_probability=success_probability,
            running_probability=running_probability,
        )

        # Parse and create ScxmlRoot
        xml_element = ET.fromstring(customized_content.encode("utf-8"))

        # Remove namespaces from all elements (required by SCXML parser)
        from as2fm.as2fm_common.common import remove_namespace

        for child in xml_element.iter():
            child.tag = remove_namespace(child.tag)

        # Set file path attribute for proper error reporting
        from as2fm.as2fm_common.logging import set_filepath_for_all_sub_elements

        set_filepath_for_all_sub_elements(xml_element, f"mock_action_{action_id}.scxml")

        return ScxmlRoot.from_xml_tree(xml_element, {})

    def generate_mock_plugins_from_bt_xml(
        self,
        bt_xml_path: str,
        condition_success_probability: float = 0.5,
        action_success_probability: float = 0.6,
        action_running_probability: float = 0.2,
    ) -> Dict[str, ScxmlRoot]:
        """
        Generate mock plugins for all conditions and actions found in a BT XML file.

        :param bt_xml_path: Path to the BT XML file
        :param condition_success_probability: Success probability for conditions
        :param action_success_probability: Success probability for actions
        :param action_running_probability: Running probability for actions
        :return: Dictionary mapping node IDs to mock SCXML plugins
        """
        mock_plugins = {}

        # Parse BT XML
        xml_tree = ET.parse(bt_xml_path, ET.XMLParser(remove_comments=True)).getroot()

        # Find all Condition and Action nodes
        for element in xml_tree.iter():
            if element.tag == "Condition" and "ID" in element.attrib:
                condition_id = element.attrib["ID"]
                mock_plugins[condition_id] = self.generate_mock_condition_plugin(
                    condition_id, condition_success_probability
                )
            elif element.tag == "Action" and "ID" in element.attrib:
                action_id = element.attrib["ID"]
                mock_plugins[action_id] = self.generate_mock_action_plugin(
                    action_id, action_success_probability, action_running_probability
                )

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


def create_mock_bt_converter_scxml(
    bt_xml_path: str,
    bt_tick_rate: float,
    tick_if_not_running: bool,
    custom_data_types: Dict[str, StructDefinition],
    seed: Optional[int] = None,
    condition_success_probability: float = 0.5,
    action_success_probability: float = 0.6,
    action_running_probability: float = 0.2,
) -> List[ScxmlRoot]:
    """
    Create a BT converter that uses SCXML template-based mock plugins.

    :param bt_xml_path: Path to the BT XML file
    :param bt_tick_rate: The rate at which the BT root is ticked
    :param tick_if_not_running: If true, keep ticking after BT stops returning RUNNING
    :param custom_data_types: Custom data type definitions
    :param seed: Random seed for reproducible mock behavior
    :param condition_success_probability: Success probability for conditions
    :param action_success_probability: Success probability for actions
    :param action_running_probability: Running probability for actions
    :return: List of generated SCXML models
    """
    from importlib.resources import files as resource_files

    # Generate mock plugins using SCXML templates
    mock_generator = MockBtPluginGenerator(seed)
    mock_plugins = mock_generator.generate_mock_plugins_from_bt_xml(
        bt_xml_path,
        condition_success_probability,
        action_success_probability,
        action_running_probability,
    )

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
            bt_plugin_scxml = load_scxml_file(str(plugin_path), custom_data_types)
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


# Convenience functions for backward compatibility
def create_mock_bt_converter(
    bt_xml_path: str,
    bt_tick_rate: float,
    tick_if_not_running: bool,
    custom_data_types: Dict[str, StructDefinition],
    seed: Optional[int] = None,
) -> List[ScxmlRoot]:
    """
    Create a BT converter using SCXML template-based mock plugins (legacy function name).

    This function provides backward compatibility with the old interface.

    :param bt_xml_path: Path to the BT XML file
    :param bt_tick_rate: The rate at which the BT root is ticked
    :param tick_if_not_running: If true, keep ticking after BT stops returning RUNNING
    :param custom_data_types: Custom data type definitions
    :param seed: Random seed for reproducible mock behavior
    :return: List of generated SCXML models
    """
    return create_mock_bt_converter_scxml(
        bt_xml_path=bt_xml_path,
        bt_tick_rate=bt_tick_rate,
        tick_if_not_running=tick_if_not_running,
        custom_data_types=custom_data_types,
        seed=seed,
        condition_success_probability=0.5,
        action_success_probability=0.6,
        action_running_probability=0.2,
    )


def generate_mock_plugins_scxml(
    bt_xml_path: str,
    condition_success_probability: float = 0.5,
    action_success_probability: float = 0.6,
    action_running_probability: float = 0.2,
    seed: Optional[int] = None,
) -> Dict[str, ScxmlRoot]:
    """
    Generate mock plugins using SCXML templates.

    :param bt_xml_path: Path to the BT XML file
    :param condition_success_probability: Success probability for conditions (default: 0.5)
    :param action_success_probability: Success probability for actions (default: 0.6)
    :param action_running_probability: Running probability for actions (default: 0.2)
    :param seed: Random seed for reproducible mock behavior
    :return: Dictionary mapping node IDs to mock SCXML plugins
    """
    generator = MockBtPluginGenerator(seed)
    return generator.generate_mock_plugins_from_bt_xml(
        bt_xml_path=bt_xml_path,
        condition_success_probability=condition_success_probability,
        action_success_probability=action_success_probability,
        action_running_probability=action_running_probability,
    )
