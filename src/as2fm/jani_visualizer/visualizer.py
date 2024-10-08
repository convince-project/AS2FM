#!/usr/bin/env python3

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

from colorsys import hsv_to_rgb
from typing import Union

from webcolors import rgb_to_hex


def _compact_assignments(assignments: Union[dict, list, str, int]) -> str:
    out: str = ""
    if isinstance(assignments, dict):
        if "ref" in assignments:
            assert "value" in assignments, "The value must be present if ref is present."
            out += f"{assignments['ref']}=({_compact_assignments(assignments['value'])})\n"
        elif "op" in assignments:
            if "left" in assignments and "right" in assignments:
                out += f"{_compact_assignments(assignments['left'])} {assignments['op']} "
                out += f"{_compact_assignments(assignments['right'])}"
            elif "exp" in assignments:
                out += f"{assignments['op']}({_compact_assignments(assignments['exp'])})"
            else:
                raise ValueError(f"Unknown assignment: {assignments}")
        elif assignments.keys() == {"exp"}:
            out += f"({_compact_assignments(assignments['exp'])})"
        else:
            raise ValueError(f"Unknown assignment: {assignments}")
    elif isinstance(assignments, list):
        for assignment in assignments:
            out += _compact_assignments(assignment)
    elif isinstance(assignments, str):
        out += assignments
    elif isinstance(assignments, int):
        out += str(assignments)
    else:
        raise ValueError(f"Unknown assignment: {assignments}")
    return out


def _unique_name(automaton_name: str, location_name: str) -> str:
    out = f"{automaton_name}_{location_name}"
    for repl in ("-", ".", "/"):
        out = out.replace(repl, "_")
    return out


class PlantUMLAutomata:
    """This represents jani automata in plantuml format."""

    def __init__(self, jani_dict: dict):
        self.jani_dict = jani_dict
        self.jani_automata = jani_dict["automata"]
        assert isinstance(self.jani_automata, list), "The automata must be a list."
        assert len(self.jani_automata) >= 1, "At least one automaton must be present."

    def _preprocess_syncs(self):
        """Preprocess the synchronizations."""
        assert "system" in self.jani_dict, "The system must be present."
        assert "syncs" in self.jani_dict["system"], "The system must have syncs."
        n_syncs = len(self.jani_dict["system"]["syncs"])
        automata = [a["name"] for a in self.jani_automata]

        # define colors for the syncs
        colors = []
        for i in range(n_syncs):
            h = i / n_syncs
            r, g, b = hsv_to_rgb(h, 1, 0.8)
            color = rgb_to_hex((int(r * 255), int(g * 255), int(b * 255)))
            colors.append(color)

        # produce a dict with automaton, action -> color
        colors_per_action = {}
        for i, sync in enumerate(self.jani_dict["system"]["syncs"]):
            synchronise = sync["synchronise"]
            assert len(synchronise) == len(
                automata
            ), "The synchronisation must have the same number of elements as the automata."
            for action, automaton in zip(synchronise, automata):
                if action is None:
                    continue
                if automaton not in colors_per_action:
                    colors_per_action[automaton] = {}
                colors_per_action[automaton][action] = colors[i]
        return colors_per_action

    def to_plantuml(
        self,
        with_assignments: bool = False,
        with_guards: bool = False,
        with_syncs: bool = False,
    ) -> str:
        colors_per_action = self._preprocess_syncs()

        puml: str = "@startuml\n"
        puml += "scale 500 width\n"

        for automaton in self.jani_automata:
            # add a box for the automaton
            automaton_name = automaton["name"]
            puml += f"package {automaton_name} {{\n"
            for i_l, location in enumerate(automaton["locations"]):
                loc_name = _unique_name(automaton_name, location["name"])
                puml += f"    usecase \"({i_l}) {location['name']}\" as {loc_name}\n"
            for edge in automaton["edges"]:
                source = _unique_name(automaton_name, edge["location"])
                assert len(edge["destinations"]) == 1, "Only one destination is supported."
                destination = edge["destinations"][0]
                target = _unique_name(automaton_name, destination["location"])
                edge_label = ""
                color = "#000"  # black by default

                # Assignments
                if (
                    with_assignments
                    and "assignments" in destination
                    and len(destination["assignments"]) > 0
                ):
                    assignments_str = _compact_assignments(destination["assignments"]).strip()
                    edge_label += f"⏬{assignments_str}\n"

                # Guards
                if with_guards and "guard" in edge:
                    guard_str = _compact_assignments(edge["guard"]).strip()
                    edge_label += f"💂{guard_str}\n"

                # Syncs
                if with_syncs and "action" in edge:
                    action = edge["action"]
                    if (
                        automaton["name"] in colors_per_action
                        and action in colors_per_action[automaton["name"]]
                    ):
                        color = colors_per_action[automaton["name"]][action]
                    edge_label += f"🔗{action}\n"

                edge_label = "  \\n\\\n".join(edge_label.split("\n"))
                if len(edge_label.strip()) > 0:
                    puml += f"    {source} -[{color}]-> {target} : {edge_label}\n"
                else:
                    puml += f"    {source} -[{color}]-> {target}\n"
            puml += "}\n"

        return puml
