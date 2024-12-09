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
Convert Behavior Trees (BT xml) to SCXML.
"""

import os
from copy import deepcopy
from importlib.resources import files as resource_files
from typing import Dict, List, Tuple

from lxml import etree as ET

from as2fm.scxml_converter.scxml_entries import (
    BtChildStatus,
    BtTickChild,
    RosRateCallback,
    RosTimeRate,
    ScxmlExecutionBody,
    ScxmlRoot,
    ScxmlState,
)

BT_ROOT_PREFIX = "bt_root_fsm_"


def is_bt_root_scxml(scxml_name: str) -> bool:
    """
    Check if the SCXML name matches with the BT root SCXML name pattern.
    """
    return scxml_name.startswith(BT_ROOT_PREFIX)


def load_available_bt_plugins(bt_plugins_scxml_paths: List[str]) -> Dict[str, ScxmlRoot]:
    available_bt_plugins = {}
    for path in bt_plugins_scxml_paths:
        assert os.path.exists(path), f"SCXML must exist. {path} not found."
        bt_plugin_scxml = ScxmlRoot.from_scxml_file(path)
        available_bt_plugins.update({bt_plugin_scxml.get_name(): bt_plugin_scxml})
    internal_bt_plugins_path = (
        resource_files("as2fm").joinpath("resources").joinpath("bt_control_nodes")
    )
    for plugin_path in internal_bt_plugins_path.iterdir():
        if plugin_path.is_file() and plugin_path.suffix == ".scxml":
            bt_plugin_scxml = ScxmlRoot.from_scxml_file(str(plugin_path))
            available_bt_plugins.update({bt_plugin_scxml.get_name(): bt_plugin_scxml})
    return available_bt_plugins


def bt_converter(
    bt_xml_path: str,
    bt_plugins_scxml_paths: List[str],
    bt_tick_rate: float,
    tick_if_not_running: bool,
) -> List[ScxmlRoot]:
    """
    Generate all Scxml files resulting from a Behavior Tree (BT) in XML format.

    :param bt_xml_path: Path to the xml file implementing the Behavior Tree.
    :param bt_plugins_scxml_paths: Paths to the scxml files implementing the BT nodes (plugins).
    :param bt_tick_rate: The rate at which the root of the input BT is ticked.
    :param tick_if_not_running: If true, keep ticking the BT root after it stops returning RUNNING.
    """
    available_bt_plugins = load_available_bt_plugins(bt_plugins_scxml_paths)
    xml_tree: ET.ElementBase = ET.parse(bt_xml_path, ET.XMLParser(remove_comments=True)).getroot()
    root_children = xml_tree.getchildren()
    assert len(root_children) == 1, f"Error: Expected one root element, found {len(root_children)}."
    assert (
        root_children[0].tag == "BehaviorTree"
    ), f"Error: Expected BehaviorTree root, found {root_children[0].tag}."
    bt_children = root_children[0].getchildren()
    assert (
        len(bt_children) == 1
    ), f"Error: Expected one BehaviorTree child, found {len(bt_children)}."
    root_child_tick_idx = 1000
    bt_name = os.path.basename(bt_xml_path).replace(".xml", "")
    bt_scxml_root = generate_bt_root_scxml(
        bt_name, root_child_tick_idx, bt_tick_rate, tick_if_not_running
    )
    generated_scxmls = [bt_scxml_root] + generate_bt_children_scxmls(
        bt_children[0], root_child_tick_idx, available_bt_plugins
    )
    return generated_scxmls


def generate_bt_root_scxml(
    scxml_name: str, tick_id: int, tick_rate: float, tick_if_not_running: bool
) -> ScxmlRoot:
    """
    Generate the root SCXML for a Behavior Tree.

    :param scxml_name: name of the scxml object to be generated.
    :param tick_id: A tick ID for the BT Root node.
    :param tick_rate: The rate at which the root is ticked.
    :param tick_if_not_running: If true, tick the BT root after it stops returning RUNNING.
    """
    bt_scxml_root = ScxmlRoot(BT_ROOT_PREFIX + scxml_name)
    ros_rate_decl = RosTimeRate(f"{scxml_name}_tick", tick_rate)
    bt_scxml_root.add_ros_declaration(ros_rate_decl)
    idle_state = ScxmlState(
        "idle",
        body=[
            RosRateCallback(ros_rate_decl, "wait_tick_res", None, [BtTickChild(0)]),
            BtChildStatus(0, "error"),
        ],
    )
    tick_res_body: ScxmlExecutionBody = (
        # In case we keep ticking after BT root finishes running
        [BtChildStatus(0, "idle")]
        if tick_if_not_running
        # In case we stop the BT after the BT root result is not RUNNING
        else [
            BtChildStatus(0, "idle", "_bt.status == RUNNING"),
            # This is the case in which BT-status != RUNNING
            BtChildStatus(0, "done"),
        ]
    )
    wait_res_state = ScxmlState(
        "wait_tick_res",
        body=tick_res_body,
    )
    bt_scxml_root.add_state(idle_state, initial=True)
    bt_scxml_root.add_state(wait_res_state)
    bt_scxml_root.add_state(ScxmlState("done"))
    bt_scxml_root.add_state(ScxmlState("error"))
    # The BT root's ID is set to -1 (unused anyway)
    bt_scxml_root.set_bt_plugin_id(-1)
    bt_scxml_root.append_bt_child_id(tick_id)
    bt_scxml_root.instantiate_bt_information()
    return bt_scxml_root


def get_bt_plugin_type(bt_xml_subtree: ET.ElementBase) -> str:
    """
    Get the BT plugin node type from the XML subtree.
    """
    plugin_type = bt_xml_subtree.tag
    assert plugin_type not in (
        "BehaviorTree",
        "SubTree",  # SubTrees support will be integrated later on
        "root",
    ), f"Error: Unexpected BT plugin tag {plugin_type}."
    if plugin_type in ("Condition", "Action"):
        plugin_type = bt_xml_subtree.attrib["ID"]
    return plugin_type


def get_bt_child_ports(bt_xml_subtree: ET.ElementBase) -> List[Tuple[str, str]]:
    """
    Get the ports of a BT child node.
    """
    ports = [(attr_key, attr_value) for attr_key, attr_value in bt_xml_subtree.attrib.items()]
    return ports


def generate_bt_children_scxmls(
    bt_xml_subtree: ET.ElementBase,
    subtree_tick_idx: int,
    available_bt_plugins: Dict[str, ScxmlRoot],
) -> List[ScxmlRoot]:
    """
    Generate the SCXML files for the children of a Behavior Tree.
    """
    generated_scxmls: List[ScxmlRoot] = []
    plugin_type = get_bt_plugin_type(bt_xml_subtree)
    assert (
        plugin_type in available_bt_plugins
    ), f"Error: BT plugin {plugin_type} not found. Available plugins: {available_bt_plugins.keys()}"
    bt_plugin_scxml = deepcopy(available_bt_plugins[plugin_type])
    bt_plugin_scxml.set_name(f"{subtree_tick_idx}_{plugin_type}")
    bt_plugin_scxml.set_bt_plugin_id(subtree_tick_idx)
    bt_plugin_scxml.set_bt_ports_values(get_bt_child_ports(bt_xml_subtree))
    generated_scxmls.append(bt_plugin_scxml)
    next_tick_idx = subtree_tick_idx + 1
    for child in bt_xml_subtree.getchildren():
        bt_plugin_scxml.append_bt_child_id(next_tick_idx)
        child_scxmls = generate_bt_children_scxmls(child, next_tick_idx, available_bt_plugins)
        generated_scxmls.extend(child_scxmls)
        next_tick_idx = generated_scxmls[-1].get_bt_plugin_id() + 1
    bt_plugin_scxml.instantiate_bt_information()
    return generated_scxmls
