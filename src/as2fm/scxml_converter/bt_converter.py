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
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.array_type import get_default_expression_for_type
from as2fm.as2fm_common.common import value_to_string_expr
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.data_types.type_utils import SCXML_DATA_STR_TO_TYPE
from as2fm.scxml_converter.scxml_entries import (
    BtChildTickStatus,
    BtTickChild,
    RosRateCallback,
    RosTimeRate,
    ScxmlAssign,
    ScxmlData,
    ScxmlDataModel,
    ScxmlParam,
    ScxmlRoot,
    ScxmlSend,
    ScxmlState,
    ScxmlTransition,
)
from as2fm.scxml_converter.scxml_entries.bt_utils import (
    BT_BLACKBOARD_EVENT_VALUE,
    BT_BLACKBOARD_GET,
    BT_BLACKBOARD_REQUEST,
    generate_bt_blackboard_set,
    get_blackboard_variable_name,
    is_blackboard_reference,
)

BT_ROOT_PREFIX = "bt_root_fsm_"


def get_blackboard_variables_from_models(models: List[ScxmlRoot]) -> Dict[str, str]:
    """
    Collect all blackboard variables and return them as a dictionary.

    :param models: List of ScxmlModel to extract the information from.
    :return: Dictionary with name and type of the detected blackboard variable.
    """
    blackboard_vars: Dict[str, str] = {}
    for scxml_model in models:
        declared_ports: List[Tuple[str, str, str]] = scxml_model.get_bt_ports_types_values()
        for p_name, p_type, p_value in declared_ports:
            assert (
                p_value is not None
            ), f"Error in model {scxml_model.get_name()}: undefined value in {p_name} BT port."
            if is_blackboard_reference(p_value):
                var_name = get_blackboard_variable_name(p_value)
                existing_bt_type = blackboard_vars.get(var_name)
                assert existing_bt_type is None or existing_bt_type == p_type
                blackboard_vars.update({var_name: p_type})
    return blackboard_vars


def generate_blackboard_scxml(bt_blackboard_vars: Dict[str, str]) -> ScxmlRoot:
    """Generate an SCXML model that handles all BT-related synchronization."""
    assert len(bt_blackboard_vars) > 0, "Cannot generate BT Blackboard, no variables"
    # TODO: Append the name of the related BT, as in generate_bt_root_scxml
    scxml_model_name = "bt_blackboard_fsm"
    state_name = "idle"
    idle_state = ScxmlState(state_name)
    bt_data: List[ScxmlData] = []
    bt_bb_param_list: List[ScxmlParam] = []
    for bb_key, bb_type in bt_blackboard_vars.items():
        default_value = value_to_string_expr(
            get_default_expression_for_type(SCXML_DATA_STR_TO_TYPE[bb_type])
        )
        bt_data.append(ScxmlData(bb_key, default_value, bb_type))
        bt_bb_param_list.append(ScxmlParam(bb_key, expr=bb_key))
        idle_state.add_transition(
            ScxmlTransition.make_single_target_transition(
                state_name,
                [generate_bt_blackboard_set(bb_key)],
                body=[ScxmlAssign(bb_key, BT_BLACKBOARD_EVENT_VALUE)],
            )
        )
    idle_state.add_transition(
        ScxmlTransition.make_single_target_transition(
            state_name,
            [BT_BLACKBOARD_REQUEST],
            body=[ScxmlSend(BT_BLACKBOARD_GET, bt_bb_param_list)],
        )
    )
    bt_root = ScxmlRoot(scxml_model_name)
    bt_root.set_data_model(ScxmlDataModel(bt_data))
    bt_root.add_state(idle_state, initial=True)
    return bt_root


def is_bt_root_scxml(scxml_name: str) -> bool:
    """
    Check if the SCXML name matches with the BT root SCXML name pattern.
    """
    return scxml_name.startswith(BT_ROOT_PREFIX)


def load_available_bt_plugins(
    bt_plugins_scxml_paths: List[str], custom_data_types: Dict[str, StructDefinition]
) -> Dict[str, ScxmlRoot]:
    available_bt_plugins = {}
    for path in bt_plugins_scxml_paths:
        assert os.path.exists(path), f"SCXML must exist. {path} not found."
        bt_plugin_scxml = ScxmlRoot.from_scxml_file(path, custom_data_types)
        available_bt_plugins.update({bt_plugin_scxml.get_name(): bt_plugin_scxml})
    internal_bt_plugins_path = (
        resource_files("as2fm").joinpath("resources").joinpath("bt_control_nodes")
    )
    for plugin_path in internal_bt_plugins_path.iterdir():
        if plugin_path.is_file() and plugin_path.suffix == ".scxml":
            bt_plugin_scxml = ScxmlRoot.from_scxml_file(str(plugin_path), custom_data_types)
            available_bt_plugins.update({bt_plugin_scxml.get_name(): bt_plugin_scxml})
    return available_bt_plugins


def bt_converter(
    bt_xml_path: str,
    bt_plugins_scxml_paths: List[str],
    bt_tick_rate: float,
    tick_if_not_running: bool,
    custom_data_types: Dict[str, StructDefinition],
) -> List[ScxmlRoot]:
    """
    Generate all Scxml files resulting from a Behavior Tree (BT) in XML format.

    :param bt_xml_path: Path to the xml file implementing the Behavior Tree.
    :param bt_plugins_scxml_paths: Paths to the scxml files implementing the BT nodes (plugins).
    :param bt_tick_rate: The rate at which the root of the input BT is ticked.
    :param tick_if_not_running: If true, keep ticking the BT root after it stops returning RUNNING.
    """
    available_bt_plugins = load_available_bt_plugins(bt_plugins_scxml_paths, custom_data_types)
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
    root_child_tick_idx = 1000
    bt_name = os.path.basename(bt_xml_path).replace(".xml", "")
    bt_scxml_root = generate_bt_root_scxml(
        bt_name, root_child_tick_idx, bt_tick_rate, tick_if_not_running
    )
    # No custom data types are required in the autogenerated BT-root
    bt_scxml_root.set_custom_data_types({})
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
            RosRateCallback.make_single_target_transition(
                ros_rate_decl, "wait_tick_res", None, [BtTickChild(0)]
            ),
            BtChildTickStatus.make_single_target_transition(0, "error"),
        ],
    )
    tick_res_body: List[ScxmlTransition] = (
        # In case we keep ticking after BT root finishes running
        [BtChildTickStatus.make_single_target_transition(0, "idle")]
        if tick_if_not_running
        # In case we stop the BT after the BT root result is not RUNNING
        else [
            BtChildTickStatus.make_single_target_transition(0, "idle", "_bt.status == RUNNING"),
            # This is the case in which BT-status != RUNNING
            BtChildTickStatus.make_single_target_transition(0, "done"),
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


def get_bt_plugin_type(bt_xml_subtree: XmlElement) -> str:
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


def get_bt_child_ports(bt_xml_subtree: XmlElement) -> List[Tuple[str, str]]:
    """
    Get the ports of a BT child node.
    """
    ports = [(attr_key, attr_value) for attr_key, attr_value in bt_xml_subtree.attrib.items()]
    return ports


def generate_bt_children_scxmls(
    bt_xml_subtree: XmlElement,
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
