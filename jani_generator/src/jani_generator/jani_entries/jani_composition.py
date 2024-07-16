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
# limitations under the License.from typing import List

"""This allows the composition of multiple automata in jani."""

from typing import Any, Dict, List, Optional


class JaniComposition:
    def __init__(self, composition_dict: Optional[Dict[str, Any]] = None):
        if composition_dict is None:
            self._elements = []
            self._syncs = []
            self._element_to_id = {}
            return
        self._elements = self._generate_elements(composition_dict["elements"])
        self._syncs = self._generate_syncs(composition_dict["syncs"])
        self._element_to_id = {element: idx for idx,
                               element in enumerate(self._elements)}
        assert self.is_valid(), "Invalid composition from dict."

    def add_element(self, element: str):
        """Append a new automaton name in the composition."""
        assert element not in self._elements, \
            f"Element {element} already exists in the composition"
        self._elements.append(element)
        self._element_to_id[element] = len(self._elements) - 1

    def get_elements(self):
        """Get the elements of the composition."""
        return self._elements

    def add_sync(self, sync_name: str, syncs: Dict[str, str]):
        """Add a new synchronisation between the elements."""
        new_sync = {
            "result": sync_name,
            "synchronise": [None] * len(self._elements)
        }
        # Generate the synchronize list
        for automata, action in syncs.items():
            assert automata in self._element_to_id, \
                f"Automaton {automata} does not exist in the composition"
            new_sync["synchronise"][self._element_to_id[automata]] = action
        self._syncs.append(new_sync)

    def get_syncs_for_element(self, element: str) -> List[str]:
        """Get the existing syncs for a specific element (=automaton)."""
        assert element in self._element_to_id, \
            f"Element {element} does not exist in the composition"
        syncs_w_none = [sync['synchronise'][self._element_to_id[element]]
                        for sync in self._syncs]
        return [sync for sync in syncs_w_none if sync is not None]

    def is_valid(self) -> bool:
        if len(self._elements) == 0:
            print("Found empty elements (automata) list.")
            return False
        for sync in self._syncs:
            if len(sync["synchronise"]) != len(self._elements):
                print("Found invalid syncs entry.")
                return False
        return True

    def _generate_elements(self, elements_list):
        elements = []
        for element in elements_list:
            elements.append(element["automaton"])
        return elements

    def _generate_syncs(self, syncs_list):
        generated_syncs = []
        for sync in syncs_list:
            assert len(self._elements) == len(
                sync["synchronise"]), "The number of elements and synchronise should be the same"
            sync_dict = {
                "synchronise": sync["synchronise"],
                "result": None
            }
            if "result" in sync:
                sync_dict["result"] = sync["result"]
            generated_syncs.append(sync_dict)
        return generated_syncs

    def as_dict(self):
        # Sort the syncs before return
        self._syncs = sorted(self._syncs, key=lambda x: x["result"])
        return {
            "elements": [{"automaton": element} for element in self._elements],
            "syncs": self._syncs
        }
