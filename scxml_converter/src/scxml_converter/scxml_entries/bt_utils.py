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

"""Collection of SCXML utilities related to BT functionalities."""

from typing import Dict, Tuple, Any, Type

import re

from scxml_converter.scxml_entries.utils import SCXML_DATA_STR_TO_TYPE


VALID_BT_INPUT_PORTS: Dict[str, Type] = SCXML_DATA_STR_TO_TYPE | {"string": str}
VALID_BT_OUTPUT_PORTS: Dict[str, Type] = SCXML_DATA_STR_TO_TYPE


def is_bt_event(event_name: str) -> bool:
    """Given an event name, returns whether it is related to a BT event or not."""
    bt_events = [f"bt_{suffix}" for suffix in ["tick", "running", "success", "failure"]]
    return event_name in bt_events


def replace_bt_event(event_name: str, instance_id: str) -> str:
    """Given a BT event name, returns the same event including the BT node instance."""
    assert is_bt_event(event_name), "Error: BT event instantiation: invalid BT event name."
    return f"bt_{instance_id}_{event_name.removeprefix('bt_')}"


def is_blackboard_reference(port_value: str) -> bool:
    """
    Check if a port value is a reference to a Blackboard variable.

    We consider a string to reference Blackboard variable if it is enclosed in curly braces.
    """
    return re.match(r"\{.+\}", port_value) is not None


class BtPortsHandler:
    """Collector for declared BT ports and their assigned value."""

    def __init__(self):
        # For each port name, store the port type string and value.
        self._in_ports: Dict[str, Tuple[str, str]] = {}
        self._out_ports: Dict[str, Tuple[Type, str]] = {}

    def in_port_exists(self, port_name: str) -> bool:
        """Check if an input port exists."""
        return port_name in self._in_ports

    def out_port_exists(self, port_name: str) -> bool:
        """Check if an output port exists."""
        return port_name in self._out_ports

    def declare_in_port(self, port_name: str, port_type: str):
        """Add an input port to the handler."""
        assert not self.in_port_exists(port_name), \
            f"Error: Port {port_name} already declared as input port."
        assert not self.out_port_exists(port_name), \
            f"Error: Port {port_name} already declared as output port."
        assert port_type in VALID_BT_INPUT_PORTS, \
            f"Error: Unsupported input port type {port_type}."
        self._in_ports[port_name] = (port_type, None)

    def declare_out_port(self, port_name: str, port_type: str):
        """Add an output port to the handler."""
        assert not self.out_port_exists(port_name), \
            f"Error: Port {port_name} already declared as output port."
        assert not self.in_port_exists(port_name), \
            f"Error: Port {port_name} already declared as input port."
        assert port_type in VALID_BT_OUTPUT_PORTS, \
            f"Error: Unsupported output port type {port_type}."
        self._out_ports[port_name] = (port_type, None)

    def set_in_port_value(self, port_name: str, port_value: Any):
        """Set the value of an input port."""
        assert self.in_port_exists(port_name), \
            f"Error: Port {port_name} is not declared as input port."
        port_type = self._in_ports[port_name][0]
        # Ensure this is not a Blackboard variable reference: currently not supported
        if is_blackboard_reference(port_value):
            raise NotImplementedError(
                f"Error: {port_value} assigns a Blackboard variable  to {port_name}. "
                "This is not yet supported.")
        self._in_ports[port_name] = (port_type, port_value)

    def get_in_port_value(self, port_name: str) -> str:
        """Get the value of an input port."""
        assert self.in_port_exists(port_name), \
            f"Error: Port {port_name} is not declared as input port."
        port_value = self._in_ports[port_name][1]
        assert port_value is not None, f"Error: Port {port_name} has no assigned value."
        return port_value