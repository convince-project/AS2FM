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

"""
SCXML base classes for BT-related classes.
"""

from copy import deepcopy
from typing import Dict, List, Optional, Type, Union

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.scxml_converter.scxml_entries import (
    ScxmlExecutionBody,
    ScxmlIf,
    ScxmlSend,
    ScxmlTransition,
    ScxmlTransitionTarget,
)
from as2fm.scxml_converter.scxml_entries.bt_utils import process_bt_child_seq_id
from as2fm.scxml_converter.scxml_entries.utils import (
    CallbackType,
    convert_expression_with_object_arrays,
    get_plain_expression,
)
from as2fm.scxml_converter.scxml_entries.xml_utils import assert_xml_tag_ok, get_xml_attribute
from as2fm.scxml_converter.xml_data_types.xml_struct_definition import XmlStructDefinition


class BtGenericRequestHandle(ScxmlTransition):
    """
    A generic class representing a transition triggered using BT interfaces (i.e. tick and halt).
    """

    @classmethod
    def get_tag_name(cls: Type["BtGenericRequestHandle"]):
        raise NotImplementedError(f"{cls.__name__} doesn't implement get_tag_name.")

    @classmethod
    def from_xml_tree_impl(
        cls: Type["BtGenericRequestHandle"],
        xml_tree: XmlElement,
        custom_data_types: Dict[str, XmlStructDefinition],
    ) -> "BtGenericRequestHandle":
        assert_xml_tag_ok(cls, xml_tree)
        condition: Optional[str] = get_xml_attribute(cls, xml_tree, "cond", undefined_allowed=True)
        transition_targets = cls.load_transition_targets_from_xml(xml_tree, custom_data_types)
        return cls(transition_targets, condition)

    @classmethod
    def make_single_target_transition(
        cls: Type["BtGenericRequestHandle"],
        target: str,
        condition: Optional[str] = None,
        body=Optional[ScxmlExecutionBody],
    ):
        """
        Generate a "traditional" bt transition with exactly one target.

        :param target: The state transition goes to. Required (unlike in SCXML specifications)
        :param condition: The condition guard to enable/disable the transition
        :param body: Content that is executed when the transition happens
        """
        return cls([ScxmlTransitionTarget(target, body=body)], condition)

    @classmethod
    def generate_bt_event_name(cls: Type[ScxmlTransition], instance_id: int):
        """
        Generate the plain scxml event associated to the BT Transition instance_id.
        """
        raise NotImplementedError(f"{cls.__name__} doesn't implement generate_bt_event_name.")

    def __init__(
        self,
        targets: List[ScxmlTransitionTarget],
        condition: Optional[str] = None,
    ):
        super().__init__(targets, [self.get_tag_name()], condition)

    def check_validity(self) -> bool:
        if len(self._targets) != 1:
            print(
                f"SCXML {self.get_tag_name()} error: "
                f"there are {len(self._targets)} targets, expecting 1."
            )
            return False
        return super().check_validity()

    def instantiate_bt_events(
        self, instance_id: int, children_ids: List[int]
    ) -> List[ScxmlTransition]:
        self._events = [self.generate_bt_event_name(instance_id)]
        self._instantiate_bt_events_in_targets(instance_id, children_ids)
        return [ScxmlTransition(self._targets, self._events, self._condition)]

    def as_xml(self) -> XmlElement:
        xml_element = super().as_xml()
        _ = xml_element.attrib.pop("event")
        return xml_element


class BtGenericRequestSend(ScxmlSend):
    """
    A generic class representing the sender of a BT related request (i.e. tick and halt)
    """

    @classmethod
    def get_tag_name(cls: Type["BtGenericRequestSend"]):
        raise NotImplementedError(f"{cls.__name__} doesn't implement get_tag_name.")

    @classmethod
    def generate_bt_event_name(cls: Type["BtGenericRequestSend"], instance_id: int):
        """
        Generate the plain scxml event associated to the BT Transition instance_id.
        """
        raise NotImplementedError(f"{cls.__name__} doesn't implement generate_bt_event_name.")

    @classmethod
    def from_xml_tree_impl(
        cls: Type["BtGenericRequestSend"], xml_tree: XmlElement, _: Dict[str, XmlStructDefinition]
    ) -> "BtGenericRequestSend":
        assert_xml_tag_ok(cls, xml_tree)
        # child_seq_id = n -> the n-th children of the control node in the BT XML
        child_seq_id: str = get_xml_attribute(cls, xml_tree, "id")
        return cls(child_seq_id)

    def __init__(self, child_seq_id: Union[str, int]):
        """
        Generate a new BtGenericRequestSend instance.

        :param child_seq_id: Which BT control node children to tick (relative the the BT-XML file).
        """
        self._child_seq_id = process_bt_child_seq_id(type(self), child_seq_id)

    def check_validity(self) -> bool:
        return isinstance(self._child_seq_id, (int, str))

    def has_bt_blackboard_input(self, _):
        """Check whether the If entry reads content from the BT Blackboard."""
        return False

    def instantiate_bt_events(
        self, instance_id: int, children_ids: List[int]
    ) -> ScxmlExecutionBody:
        """
        Convert the BtGenericRequestSend to plain SCXML.

        Returns an ScxmlSend if the child id is constant and an ScxmlIf otherwise.
        """
        if isinstance(self._child_seq_id, int):
            # We know the exact child ID we want to send the request to
            assert self._child_seq_id < len(children_ids), (
                f"Error: SCXML {self.get_tag_name()}: invalid child ID {self._child_seq_id} "
                f"for {len(children_ids)} children."
            )
            return [ScxmlSend(self.generate_bt_event_name(children_ids[self._child_seq_id]))]
        else:
            # The children id to reach depends on the runtime value of self._child_seq_id
            if_bodies = []
            for child_seq_n, child_id in enumerate(children_ids):
                if_bodies.append(
                    (
                        f"{self._child_seq_id} == {child_seq_n}",
                        [ScxmlSend(self.generate_bt_event_name(child_id))],
                    )
                )
            return ScxmlIf(if_bodies).instantiate_bt_events(instance_id, children_ids)

    def as_xml(self) -> XmlElement:
        """
        Return the instance content as an XML Element.
        """
        xml_bt_tick_child = ET.Element(self.get_tag_name(), {"id": str(self._child_seq_id)})
        return xml_bt_tick_child


class BtGenericStatusHandle(ScxmlTransition):
    """
    Process a generic response received from a BT child.
    """

    @classmethod
    def get_tag_name(cls: Type["BtGenericStatusHandle"]):
        raise NotImplementedError(f"{cls.__name__} doesn't implement get_tag_name.")

    @classmethod
    def generate_bt_event_name(cls: Type["BtGenericStatusHandle"], instance_id: int):
        """
        Generate the plain scxml event associated to the BT Transition instance_id.
        """
        raise NotImplementedError(f"{cls.__name__} doesn't implement generate_bt_event_name.")

    @classmethod
    def from_xml_tree_impl(
        cls: Type["BtGenericStatusHandle"],
        xml_tree,
        custom_data_types: Dict[str, XmlStructDefinition],
    ) -> "BtGenericStatusHandle":
        assert_xml_tag_ok(cls, xml_tree)
        # Same as in BtTickChild
        child_seq_id = get_xml_attribute(cls, xml_tree, "id")
        condition = get_xml_attribute(cls, xml_tree, "cond", undefined_allowed=True)
        targets = cls.load_transition_targets_from_xml(xml_tree, custom_data_types)
        return cls(child_seq_id, targets, condition)

    @classmethod
    def make_single_target_transition(
        cls: Type["BtGenericStatusHandle"],
        child_seq_id: Union[str, int],
        target: str,
        condition: Optional[str] = None,
        body: Optional[ScxmlExecutionBody] = None,
    ):
        """
        Generate a BtGenericStatusHandle with exactly one target.

        :param child_seq_id: From which BT children ID we receive the response.
        :param target: The state transition goes to. Required (unlike in SCXML specifications)
        :param condition: The condition guard to enable/disable the transition
        :param body: Content that is executed when the transition happens
        """
        targets = [ScxmlTransitionTarget(target, None, body)]
        return cls(child_seq_id, targets, condition)

    def __init__(
        self,
        child_seq_id: Union[str, int],
        targets: List[ScxmlTransitionTarget],
        condition: Optional[str] = None,
    ):
        """
        Generate an instance of a handler for a generic BT Child reply.

        :param child_seq_id: Which BT child is the response related to.
        :param targets: The targets to use for transitioning to new states.
        :param condition: The condition to check before transitioning.
        """
        super().__init__(targets, condition=condition)
        self._child_seq_id = process_bt_child_seq_id(type(self), child_seq_id)

    def instantiate_bt_events(
        self, instance_id: int, children_ids: List[int]
    ) -> List[ScxmlTransition]:
        plain_cond_expr = None
        if self._condition is not None:
            plain_cond_expr = get_plain_expression(self._condition, CallbackType.BT_RESPONSE, None)
        if isinstance(self._child_seq_id, int):
            # Handling specific child seq. ID, return a single transition
            assert self._child_seq_id < len(children_ids), (
                f"Error: SCXML BT Child Status: invalid child seq. ID {self._child_seq_id} "
                f"for {len(children_ids)} children."
            )
            target_child_id = children_ids[self._child_seq_id]
            return ScxmlTransition(
                self._targets, [self.generate_bt_event_name(target_child_id)], plain_cond_expr
            ).instantiate_bt_events(instance_id, children_ids)
        else:
            # Handling a generic child ID, return a transition for each child
            condition_prefix = "" if plain_cond_expr is None else f"({plain_cond_expr}) && "
            generated_transitions = []
            for child_seq_n, child_id in enumerate(children_ids):
                child_cond = convert_expression_with_object_arrays(
                    f"{condition_prefix} ({self._child_seq_id} == {child_seq_n})"
                )
                # Make a copy per set of targets: might create issues when adding targets otherwise
                generated_transition = ScxmlTransition(
                    deepcopy(self._targets),
                    [self.generate_bt_event_name(child_id)],
                    child_cond,
                ).instantiate_bt_events(instance_id, children_ids)
                assert (
                    len(generated_transition) == 1
                ), "Error: SCXML BT Child Status: Expected a single transition."
                generated_transitions.append(generated_transition[0])
            return generated_transitions

    def as_xml(self) -> XmlElement:
        xml_element = super().as_xml()
        assert self._events is None, f"Error: SCXML {self.get_tag_name()}: Expected no events."
        xml_element.set("id", str(self._child_seq_id))
        return xml_element


class BtGenericStatusSend(ScxmlSend):
    """
    Send a generic response to a BT parent node.
    """

    @classmethod
    def get_tag_name(cls: Type["BtGenericStatusSend"]):
        raise NotImplementedError(f"{cls.__name__} doesn't implement get_tag_name.")

    @classmethod
    def from_xml_tree_impl(
        cls: Type["BtGenericStatusSend"], xml_tree: XmlElement, _: Dict[str, XmlStructDefinition]
    ) -> "BtGenericStatusSend":
        assert_xml_tag_ok(cls, xml_tree)
        return cls()

    @classmethod
    def generate_bt_event_name(cls: Type["BtGenericStatusSend"], instance_id: int):
        """
        Generate the plain scxml event associated to the BT Transition instance_id.
        """
        raise NotImplementedError(f"{cls.__name__} doesn't implement generate_bt_event_name.")

    def __init__(self):
        pass

    def check_validity(self) -> bool:
        return True

    def has_bt_blackboard_input(self, _) -> bool:
        """We do not expect reading from BT Ports here. Return False!"""
        return False

    def instantiate_bt_events(self, instance_id: int, _) -> ScxmlExecutionBody:
        return [ScxmlSend(self.generate_bt_event_name(instance_id))]

    def as_xml(self) -> XmlElement:
        return ET.Element(self.get_tag_name())
