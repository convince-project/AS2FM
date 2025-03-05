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
SCXML entries related to Behavior Tree Ticks and related responses.
"""

from typing import List, Optional, Union

from lxml import etree as ET

from as2fm.scxml_converter.scxml_entries import ScxmlParam, ScxmlSend, ScxmlTransitionTarget
from as2fm.scxml_converter.scxml_entries.bt_utils import (
    BtResponse,
    generate_bt_halt_event,
    generate_bt_halt_response_event,
    generate_bt_tick_event,
    generate_bt_tick_response_event,
)
from as2fm.scxml_converter.scxml_entries.scxml_bt_base import (
    BtGenericRequestHandle,
    BtGenericRequestSend,
    BtGenericStatusHandle,
    BtGenericStatusSend,
)
from as2fm.scxml_converter.scxml_entries.xml_utils import assert_xml_tag_ok, get_xml_attribute


class BtTick(BtGenericRequestHandle):
    """
    Process a BT plugin/control node tick, triggering the related transition.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "bt_tick"

    @staticmethod
    def generate_bt_event_name(instance_id: int):
        """
        Generate the plain scxml event name for this BT tick instance_id.
        """
        return generate_bt_tick_event(instance_id)


class BtHalt(BtGenericRequestHandle):
    """
    Process a BT plugin/control node halt / reset, triggering the related transition.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "bt_halt"

    @staticmethod
    def generate_bt_event_name(instance_id: int):
        """
        Generate the plain scxml event name for this BT tick instance_id.
        """
        return generate_bt_halt_event(instance_id)

    def check_validity(self) -> bool:
        if self._condition is not None:
            print(
                f"SCXML {self.get_tag_name()} error: "
                f"no conditions expected when halting a BT Node."
            )
            return False
        return super().check_validity()


class BtTickChild(BtGenericRequestSend):
    """Tick one child of a BT control node."""

    @staticmethod
    def get_tag_name() -> str:
        return "bt_tick_child"

    @staticmethod
    def generate_bt_event_name(instance_id: int):
        """
        Generate the plain scxml event name for this BT tick instance_id.
        """
        return generate_bt_tick_event(instance_id)


class BtHaltChild(BtGenericRequestSend):
    """Halt one child of a BT control node."""

    @staticmethod
    def get_tag_name() -> str:
        return "bt_halt_child"

    @staticmethod
    def generate_bt_event_name(instance_id: int):
        """
        Generate the plain scxml event name for this BT tick instance_id.
        """
        return generate_bt_halt_event(instance_id)


class BtChildTickStatus(BtGenericStatusHandle):
    """
    Process the response received from a BT child.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "bt_child_status"

    @staticmethod
    def generate_bt_event_name(instance_id: int):
        """
        Generate the plain scxml event name for this BT tick Status handler.
        """
        return generate_bt_tick_response_event(instance_id)

    def __init__(
        self,
        child_seq_id: Union[str, int],
        targets: List[ScxmlTransitionTarget],
        condition: Optional[str] = None,
    ):
        """
        Generate a BtChildTickStatus instance.

        :param child_seq_id: Which BT control node children to tick (relative to the BT-XML file).
        :param targets: All possible targets available when executing this transition.
        :param condition: A condition that must be satisfied before executing this transition.
        """
        super().__init__(child_seq_id, targets, condition)
        if self._condition is not None:
            # Substitute the responses string with the corresponding integer
            self._condition = BtResponse.process_expr(self._condition)


class BtChildHaltedHandle(BtGenericStatusHandle):
    """
    Process the response received from a BT child.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "bt_child_halted"

    @staticmethod
    def generate_bt_event_name(instance_id: int):
        """
        Generate the plain scxml event name for this BT tick Status handler.
        """
        return generate_bt_halt_response_event(instance_id)


class BtReturnTickStatus(BtGenericStatusSend):
    """
    Send a BT tick status response to the BT parent node.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "bt_return_status"

    @staticmethod
    def generate_bt_event_name(instance_id: int) -> str:
        return generate_bt_tick_response_event(instance_id)

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "BtReturnTickStatus":
        assert_xml_tag_ok(BtReturnTickStatus, xml_tree)
        status = get_xml_attribute(BtReturnTickStatus, xml_tree, "status")
        return BtReturnTickStatus(status)

    def __init__(self, status: str):
        self._status: str = status
        self._status_id: int = BtResponse.str_to_int(status)

    def check_validity(self) -> bool:
        return True

    def has_bt_blackboard_input(self, _) -> bool:
        """We do not expect reading from BT Ports here. Return False!"""
        return False

    def instantiate_bt_events(self, instance_id: int, children_ids: List[int]) -> List[ScxmlSend]:
        plain_send = super().instantiate_bt_events(instance_id, children_ids)
        plain_send[0].append_param(ScxmlParam("status", expr=f"{self._status_id}"))
        return plain_send

    def as_xml(self) -> ET.Element:
        ret_xml = super().as_xml()
        ret_xml.set("status", self._status)
        return ret_xml


class BtReturnHalted(BtGenericStatusSend):
    """
    Send a BT tick status response to the BT parent node.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "bt_return_halted"

    @staticmethod
    def generate_bt_event_name(instance_id: int) -> str:
        return generate_bt_halt_response_event(instance_id)

    def check_validity(self) -> bool:
        return True

    def has_bt_blackboard_input(self, _) -> bool:
        """We do not expect reading from BT Ports here. Return False!"""
        return False
