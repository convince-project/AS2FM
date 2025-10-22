# Copyright (c) 2025 - for information on the respective copyright owner
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

from typing import List, Optional, Tuple, Type, Union, get_args

from as2fm.scxml_converter.ascxml_extensions import AscxmlDeclaration
from as2fm.scxml_converter.ascxml_extensions.bt_entries import BtPortDeclarations
from as2fm.scxml_converter.ascxml_extensions.ros_entries import AscxmlRootROS, RosDeclaration

ValidDeclarationTypes = Union[RosDeclaration, BtPortDeclarations]


class AscxmlRootBT(AscxmlRootROS):
    """
    The main entry point of specialized ASCXML Models for ROS nodes.
    In XML, it uses the tag `ascxml`.
    """

    @classmethod
    def get_declaration_classes(cls) -> List[Type[AscxmlDeclaration]]:
        return AscxmlRootROS.get_declaration_classes() + list(get_args(BtPortDeclarations))

    def __init__(self, name):
        super().__init__(name)
        self._bt_plugin_id: Optional[int] = None
        self._bt_children_ids: List[int] = []

    def set_bt_plugin_id(self, instance_id: int) -> None:
        """Update all BT-related events to use the assigned instance ID."""
        self._bt_plugin_id = instance_id

    def get_bt_plugin_id(self) -> Optional[int]:
        """Get the ID of the BT plugin instance, if any."""
        return self._bt_plugin_id

    def add_declaration(self, ros_bt_declaration: ValidDeclarationTypes):
        """Add a new ROS or BT declaration to the ASCXML model"""
        assert isinstance(
            ros_bt_declaration, get_args(ValidDeclarationTypes)
        ), "Error: ASCXML root: invalid declaration type."
        assert ros_bt_declaration.check_validity(), "Error: ASCXML root: invalid declaration."
        self._ascxml_declarations.append(ros_bt_declaration)

    def set_bt_port_value(self, port_name: str, port_value: str):
        """Set the value of an input port."""
        # TODO: Move the value holding to the BT Port declaration object
        pass

    def set_bt_ports_values(self, ports_values: List[Tuple[str, str]]):
        """Set the values of multiple input ports."""
        for port_name, port_value in ports_values:
            self.set_bt_port_value(port_name, port_value)

    def get_bt_ports_types_values(self) -> List[Tuple[str, str, str]]:
        """
        Get information about the BT ports in the model.

        :return: A list of Tuples containing bt_port_name, type and value.
        """
        # TODO: Update it to extract the value directly from the BT Port declarations
        return [
            (p_name, p_type, p_value)
            for p_name, (p_type, p_value) in self._bt_ports_handler.get_all_ports().items()
        ]

    def append_bt_child_id(self, child_id: int):
        """Append a child ID to the list of child IDs."""
        assert isinstance(child_id, int), "Error: SCXML root: invalid child ID type."
        self._bt_children_ids.append(child_id)

    def instantiate_bt_information(self):
        """Instantiate the values of BT ports and children IDs in the SCXML entries."""
        n_bt_children = len(self._bt_children_ids)
        assert self._bt_plugin_id is not None, "Error: SCXML root: BT plugin ID not set."
        # Automatically add the correct amount of children to the specific port
        if self._bt_ports_handler.in_port_exists("CHILDREN_COUNT"):
            self._bt_ports_handler.set_port_value("CHILDREN_COUNT", str(n_bt_children))
        self._data_model.update_bt_ports_values(self._bt_ports_handler)
        for ros_decl_scxml in self._ros_declarations:
            ros_decl_scxml.update_bt_ports_values(self._bt_ports_handler)
        for scxml_thread in self._additional_threads:
            scxml_thread.update_bt_ports_values(self._bt_ports_handler)
        processed_states: List[ScxmlState] = []
        for state in self._states:
            processed_states.extend(
                state.instantiate_bt_events(
                    self._bt_plugin_id, self._bt_children_ids, self._bt_ports_handler
                )
            )
        self._states = processed_states
