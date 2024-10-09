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
import re
from copy import deepcopy
from enum import Enum, auto
from typing import List

from btlib.bt_to_fsm.bt_to_fsm import Bt2FSM
from btlib.bts import xml_to_networkx
from btlib.common import NODE_CAT
from lxml import etree as ET

from as2fm.scxml_converter.scxml_entries import (
    RESERVED_BT_PORT_NAMES,
    BtChildStatus,
    BtTickChild,
    RosRateCallback,
    RosTimeRate,
    ScxmlRoot,
    ScxmlSend,
    ScxmlState,
    ScxmlTransition,
)


class BT_EVENT_TYPE(Enum):
    """Event types for Behavior Tree."""

    TICK = auto()
    SUCCESS = auto()
    FAILURE = auto()
    RUNNING = auto()

    @staticmethod
    def from_str(event_name: str) -> "BT_EVENT_TYPE":
        event_name = event_name.replace("event=", "")
        event_name = event_name.replace('"', "")
        event_name = event_name.replace("bt_", "")
        return BT_EVENT_TYPE[event_name.upper()]


def bt_event_name(node_id: str, event_type: BT_EVENT_TYPE) -> str:
    """Return the event name for the given node and event type."""
    return f"bt_{node_id}_{event_type.name.lower()}"


def bt_converter(
    bt_xml_path: str, bt_plugins_scxml_paths: List[str], bt_tick_rate: float
) -> List[ScxmlRoot]:
    """
    Convert a Behavior Tree (BT) in XML format to SCXML.

    Args:
        bt_xml_path: The path to the Behavior Tree in XML format.
        bt_plugins_scxml_paths: The paths to the SCXML files of BT plugins.
        bt_tick_rate: The rate at which the BT should tick.

    Returns:
        A list of the generated SCXML objects.
    """
    bt_graph, _ = xml_to_networkx(bt_xml_path)

    bt_plugins_scxmls = {}
    for path in bt_plugins_scxml_paths:
        assert os.path.exists(path), f"SCXML must exist. {path} not found."
        bt_plugin_scxml = ScxmlRoot.from_scxml_file(path)
        bt_plugin_name = bt_plugin_scxml.get_name()
        assert (
            bt_plugin_name not in bt_plugins_scxmls
        ), f"Plugin name must be unique. {bt_plugin_name} already exists."
        bt_plugins_scxmls[bt_plugin_name] = bt_plugin_scxml

    leaf_node_ids = []
    generated_scxmls: List[ScxmlRoot] = []
    # Generate the instances of the plugins used in the BT
    for node in bt_graph.nodes:
        assert "category" in bt_graph.nodes[node], "Node must have a category."
        if bt_graph.nodes[node]["category"] == NODE_CAT.LEAF:
            leaf_node_ids.append(node)
            assert "ID" in bt_graph.nodes[node], "Leaf node must have a type."
            node_type = bt_graph.nodes[node]["ID"]
            node_id = node
            assert (
                node_type in bt_plugins_scxmls
            ), f"Leaf node must have a plugin. {node_type} not found."
            instance_name = f"{node_id}_{node_type}"
            scxml_plugin_instance: ScxmlRoot = deepcopy(bt_plugins_scxmls[node_type])
            scxml_plugin_instance.set_name(instance_name)
            scxml_plugin_instance.set_bt_plugin_id(node_id)
            bt_ports = [
                (p_name, p_value)
                for p_name, p_value in bt_graph.nodes[node].items()
                if p_name not in RESERVED_BT_PORT_NAMES
            ]
            scxml_plugin_instance.set_bt_ports_values(bt_ports)
            scxml_plugin_instance.instantiate_bt_information()
            assert (
                scxml_plugin_instance.check_validity()
            ), f"Error: SCXML plugin instance {instance_name} is not valid."
            generated_scxmls.append(scxml_plugin_instance)
    # Generate the BT SCXML
    fsm_graph = Bt2FSM(bt_graph).convert()
    bt_scxml_root = ScxmlRoot("bt")
    name_with_id_pattern = re.compile(r"[0-9]+_.+")
    for node in fsm_graph.nodes:
        state = ScxmlState(node)
        node_id = None
        if name_with_id_pattern.match(node):
            node_id = int(node.split("_")[0])
            if node_id in leaf_node_ids:
                state.append_on_entry(ScxmlSend(bt_event_name(node_id, BT_EVENT_TYPE.TICK)))
        for edge in fsm_graph.edges(node):
            target = edge[1]
            transition = ScxmlTransition(target)
            if node_id is not None and node_id in leaf_node_ids:
                if "label" not in fsm_graph.edges[edge]:
                    continue
                label = fsm_graph.edges[edge]["label"]
                if label == "on_success":
                    event_type = BT_EVENT_TYPE.SUCCESS
                elif label == "on_failure":
                    event_type = BT_EVENT_TYPE.FAILURE
                elif label == "on_running":
                    event_type = BT_EVENT_TYPE.RUNNING
                else:
                    raise ValueError(f"Invalid label: {label}")
                event_name = bt_event_name(node_id, event_type)
                transition.add_event(event_name)
            state.add_transition(transition)
        if node in ["success", "failure", "running"]:
            state.add_transition(ScxmlTransition("wait_for_tick"))
        bt_scxml_root.add_state(state)
    # TODO: Make BT rate configurable, e.g. from main.xml
    rtr = RosTimeRate("bt_tick", bt_tick_rate)
    bt_scxml_root.add_ros_declaration(rtr)

    wait_for_tick = ScxmlState("wait_for_tick")
    wait_for_tick.add_transition(RosRateCallback(rtr, "tick"))
    bt_scxml_root.add_state(wait_for_tick, initial=True)
    assert bt_scxml_root.check_validity(), "Error: SCXML root tag is not valid."
    generated_scxmls.append(bt_scxml_root)

    return generated_scxmls


def bt_converter_new(
    bt_xml_path: str, bt_plugins_scxml_paths: List[str], bt_tick_rate: float
) -> List[ScxmlRoot]:
    """
    Generate all Scxml files resulting from a Behavior Tree (BT) in XML format.
    """
    xml_tree: ET.ElementBase = ET.parse(bt_xml_path).getroot()
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
    bt_scxml_root = generate_bt_root_scxml(bt_name, root_child_tick_idx, bt_tick_rate)
    generated_scxmls = [bt_scxml_root] + generate_bt_children_scxmls(
        bt_children[0], root_child_tick_idx, bt_plugins_scxml_paths
    )
    return generated_scxmls


def generate_bt_root_scxml(scxml_name: str, tick_id: int, tick_rate: float) -> ScxmlRoot:
    """
    Generate the root SCXML for a Behavior Tree.
    """
    bt_scxml_root = ScxmlRoot(scxml_name)
    ros_rate_decl = RosTimeRate(f"{scxml_name}_tick", tick_rate)
    bt_scxml_root.add_ros_declaration(ros_rate_decl)
    idle_state = ScxmlState(
        "idle", body=[RosRateCallback(ros_rate_decl, "wait_tick_res", None, [BtTickChild(0)])]
    )
    wait_res_state = ScxmlState(
        "wait_tick_res", body=[RosRateCallback(ros_rate_decl, "error"), BtChildStatus(0, "idle")]
    )
    error_state = ScxmlState("error")
    bt_scxml_root.add_state(idle_state, initial=True)
    bt_scxml_root.add_state(wait_res_state)
    bt_scxml_root.add_state(error_state)
    # TODO: BT children handling  interface must be finalized
    bt_scxml_root.append_bt_child_id(tick_id)
    bt_scxml_root.instantiate_bt_information()
    return bt_scxml_root


def generate_bt_children_scxmls(
    bt_xml_tree: ET.ElementBase, root_child_tick_idx: int, bt_plugins_scxml_paths: List[str]
) -> List[ScxmlRoot]:
    """
    Generate the SCXML files for the children of a Behavior Tree.
    """
    pass
