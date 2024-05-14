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

"""An automaton for jani."""

from typing import List, Dict, Set, Optional
from jani_generator.jani_entries import JaniEdge, JaniConstant, JaniVariable, JaniExpression


class JaniAutomaton:
    def __init__(self, *, automaton_dict: Optional[dict] = None):
        self._locations: Set[str] = set()
        self._initial_locations: Set[str] = set()
        self._local_variables: Dict[str, JaniVariable] = {}
        self._edges: List[JaniEdge] = []
        # Id to autogenerate edge action name if not provided
        self._edge_id = 0
        if automaton_dict is None:
            return
        self._name = automaton_dict["name"]
        self._generate_locations(
            automaton_dict["locations"], automaton_dict["initial-locations"])
        self._generate_variables(automaton_dict["variables"])
        self._generate_edges(automaton_dict["edges"])

    def get_name(self):
        return self._name

    def set_name(self, name: str):
        self._name = name

    def add_location(self, location_name: str, is_initial: bool = False):
        self._locations.add(location_name)
        if is_initial:
            self._initial_locations.add(location_name)

    def get_initial_locations(self) -> Set[str]:
        return self._initial_locations

    def make_initial(self, location_name: str):
        assert location_name in self._locations, \
            f"Location {location_name} must exist in the automaton"
        self._initial_locations.add(location_name)

    def unset_initial(self, location_name: str):
        assert location_name in self._locations, \
            f"Location {location_name} must exist in the automaton"
        assert location_name in self._initial_locations, \
            f"Location {location_name} must be initial"
        self._initial_locations.remove(location_name)

    def add_variable(self, variable: JaniVariable):
        self._local_variables.update({variable.name(): variable})

    def get_variables(self) -> Dict[str, JaniVariable]:
        return self._local_variables

    def add_edge(self, edge: JaniEdge):
        if edge.get_action() is None:
            edge.set_action(f"{self._name}_action_{self._edge_id}")
            self._edge_id += 1
        self._edges.append(edge)

    def get_edges(self) -> List[JaniEdge]:
        return self._edges

    def _generate_locations(self, location_list: List[str], initial_locations: List[str]):
        for location in location_list:
            self._locations.add(location["name"])
        for init_location in initial_locations:
            self._initial_locations.add(init_location)

    def _generate_variables(self, variable_list: List[dict]):
        for variable in variable_list:
            init_expr = None
            if "initial-value" in variable:
                init_expr = JaniExpression(variable["initial-value"])
            is_transient = False
            if "transient" in variable:
                is_transient = variable["transient"]
            var_type = JaniVariable.jani_type_from_string(variable["type"])
            self._local_variables.update({variable["name"]: JaniVariable(
                variable["name"], var_type, init_expr, is_transient)})

    def _generate_edges(self, edge_list: List[dict]):
        # TODO: Proposal -> Edges might require support variables? In case we want to provide standard ones...
        for edge in edge_list:
            jani_edge = JaniEdge(edge)
            self.add_edge(jani_edge)

    def get_actions(self) -> Set[JaniEdge]:
        actions = set()
        for edge in self._edges:
            actions.add(edge.get_action())
        return actions

    def merge(self, other: 'JaniAutomaton'):
        assert self._name == other.get_name(), "Automaton names must match"
        self._locations.update(other._locations)
        self._initial_locations.update(other._initial_locations)
        self._local_variables.update(other._local_variables)
        self._edges.extend(other._edges)

    def as_dict(self, constant: Dict[str, JaniConstant]):
        automaton_dict = {
            "name": self._name,
            "locations": [{"name": location} for location in sorted(self._locations)],
            "initial-locations": sorted(list(self._initial_locations)),
            "edges": [edge.as_dict(constant) for edge in self._edges]
        }
        if len(self._local_variables) > 0:
            automaton_dict.update(
                {"variables": [jani_var.as_dict() for jani_var in self._local_variables.values()]})
        return automaton_dict
