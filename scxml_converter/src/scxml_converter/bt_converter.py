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
import xml.etree.ElementTree as ET
from enum import Enum, auto
from typing import List

import networkx as nx
from btlib.bt_to_fsm.bt_to_fsm import Bt2FSM
from btlib.bts import xml_to_networkx
from btlib.common import NODE_CAT

from scxml_converter.scxml_entries import (RosRateCallback, RosTimeRate,
                                           ScxmlRoot, ScxmlSend, ScxmlState,
                                           ScxmlTransition)


class BT_EVENT_TYPE(Enum):
    """Event types for Behavior Tree."""
    TICK = auto()
    SUCCESS = auto()
    FAILURE = auto()
    RUNNING = auto()

    def from_str(event_name: str) -> 'BT_EVENT_TYPE':
        event_name = event_name.replace('event=', '')
        event_name = event_name.replace('"', '')
        event_name = event_name.replace('bt_', '')
        return BT_EVENT_TYPE[event_name.upper()]


def bt_event_name(node_id: str, event_type: BT_EVENT_TYPE) -> str:
    """Return the event name for the given node and event type."""
    return f'bt_{node_id}_{event_type.name.lower()}'


def bt_converter(
    bt_xml_path: str,
    bt_plugins_scxml_paths: List[str],
    output_folder: str
):
    """
    Convert a Behavior Tree (BT) in XML format to SCXML.

    Args:
        bt_xml_path: The path to the Behavior Tree in XML format.
        bt_plugins_scxml_paths: The paths to the SCXML files of BT plugins.
        output_folder: The folder where the SCXML files will be saved.

    Returns:
        A list of the generated SCXML files.
    """
    bt_graph, xpi = xml_to_networkx(bt_xml_path)
    generated_files = []

    bt_plugins_scxml = {}
    for path in bt_plugins_scxml_paths:
        assert os.path.exists(path), f'SCXML must exist. {path} not found.'
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            xml = ET.fromstring(content)
            name = xml.attrib['name']
            assert name not in bt_plugins_scxml, \
                f'Plugin name must be unique. {name} already exists.'
            bt_plugins_scxml[name] = content

    leaf_node_ids = []
    for node in bt_graph.nodes:
        assert 'category' in bt_graph.nodes[node], 'Node must have a category.'
        if bt_graph.nodes[node]['category'] == NODE_CAT.LEAF:
            leaf_node_ids.append(node)
            assert 'NAME' in bt_graph.nodes[node], 'Leaf node must have a type.'
            node_type = bt_graph.nodes[node]['NAME']
            node_id = node
            assert node_type in bt_plugins_scxml, \
                f'Leaf node must have a plugin. {node_type} not found.'
            instance_name = f'{node_id}_{node_type}'
            output_fname = os.path.join(
                output_folder, f'{instance_name}.scxml')
            generated_files.append(output_fname)
            this_plugin_content = bt_plugins_scxml[node_type]
            event_names_to_replace = [
                f'bt_{t}' for t in [
                    'tick', 'success', 'failure', 'running']]
            for event_name in event_names_to_replace:
                declaration_old = f'event="{event_name}"'
                new_event_name = bt_event_name(
                    node_id, BT_EVENT_TYPE.from_str(event_name))
                declaration_new = f'event="{new_event_name}"'
                this_plugin_content = this_plugin_content.replace(
                    declaration_old, declaration_new)
            # TODO: Replace arguments from the BT xml file.
            # TODO: Change name to instance name
            with open(output_fname, 'w', encoding='utf-8') as f:
                f.write(this_plugin_content)
    fsm_graph = Bt2FSM(bt_graph).convert()
    output_file_bt = os.path.join(output_folder, 'bt.scxml')
    generated_files.append(output_file_bt)

    root_tag = ScxmlRoot("bt")
    for node in fsm_graph.nodes:
        state = ScxmlState(node)
        if '_' in node:
            node_id = int(node.split('_')[0])
        else:
            node_id = None
        if node_id and node_id in leaf_node_ids:
            state.append_on_entry(ScxmlSend(
                bt_event_name(node_id, BT_EVENT_TYPE.TICK)))
        for edge in fsm_graph.edges(node):
            target = edge[1]
            transition = ScxmlTransition(target)
            if node_id and node_id in leaf_node_ids:
                if 'label' not in fsm_graph.edges[edge]:
                    continue
                label = fsm_graph.edges[edge]['label']
                if label == 'on_success':
                    event_type = BT_EVENT_TYPE.SUCCESS
                elif label == 'on_failure':
                    event_type = BT_EVENT_TYPE.FAILURE
                elif label == 'on_running':
                    event_type = BT_EVENT_TYPE.RUNNING
                else:
                    raise ValueError(f'Invalid label: {label}')
                event_name = bt_event_name(node_id, event_type)
                transition.add_event(event_name)
            state.add_transition(transition)
        if node in ['success', 'failure', 'running']:
            state.add_transition(
                ScxmlTransition("wait_for_tick"))
        root_tag.add_state(state)

    rtr = RosTimeRate("bt_tick", 1.0)
    root_tag.add_ros_declaration(rtr)

    wait_for_tick = ScxmlState("wait_for_tick")
    wait_for_tick.add_transition(
        RosRateCallback(rtr, "tick"))
    root_tag.add_state(wait_for_tick, initial=True)

    assert root_tag.check_validity(), "Error: SCXML root tag is not valid."

    with open(output_file_bt, 'w', encoding='utf-8') as f:
        f.write(ET.tostring(root_tag.as_xml(), encoding='unicode', xml_declaration=True))

    return generated_files
