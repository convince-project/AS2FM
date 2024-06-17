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

from enum import Enum, auto
from typing import List
import os
import xml.etree.ElementTree as ET

import networkx as nx

from btlib.bt_to_fsm.bt_to_fsm import Bt2FSM
from btlib.bts import xml_to_networkx
from btlib.common import NODE_CAT

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
        output_path: str
    ):
    """
    Convert a Behavior Tree (BT) in XML format to SCXML.

    Args:
        bt_xml_path: The path to the Behavior Tree in XML format.
        bt_plugins_scxml_paths: The paths to the SCXML files of BT plugins.

    Returns:
        The SCXML representation of the Behavior Tree.

    """
    bt_graph, xpi = xml_to_networkx(bt_xml_path)

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

    for node in bt_graph.nodes:
        assert 'category' in bt_graph.nodes[node], 'Node must have a category.'
        if bt_graph.nodes[node]['category'] == NODE_CAT.LEAF:
            assert 'NAME' in bt_graph.nodes[node], 'Leaf node must have a type.'
            node_type = bt_graph.nodes[node]['NAME']
            node_id = node
            assert node_type in bt_plugins_scxml, \
                f'Leaf node must have a plugin. {node_type} not found.'
            instance_name = f'{node_id}_{node_type}'
            output_fname = os.path.join(output_path, f'{instance_name}.scxml')
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
            with open(output_fname, 'w', encoding='utf-8') as f:
                f.write(bt_plugins_scxml[node_type])

    fsm_graph = Bt2FSM(bt_graph).convert()
    output_file_bt = os.path.join(output_path, 'bt.scxml')
    with open(output_file_bt, 'w', encoding='utf-8') as f:
        f.write("<!-- TODO -->")
    print(nx.info(fsm_graph))