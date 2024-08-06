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

"""And edge defining the possible transition from one state to another in jani."""

from typing import Dict, Optional

from jani_generator.jani_entries import (JaniAssignment, JaniConstant,
                                         JaniExpression, JaniGuard)
from jani_generator.jani_entries.jani_convince_expression_expansion import \
    expand_expression


class JaniEdge:
    def __init__(self, edge_dict: dict):
        self.location = edge_dict["location"]
        self.action: str = None
        if "action" in edge_dict:
            self.action = edge_dict["action"]
        self.guard = None
        if "guard" in edge_dict:
            self.guard = JaniGuard(edge_dict["guard"])
        self.destinations = []
        for dest in edge_dict["destinations"]:
            jani_destination = {
                "location": dest["location"],
                "probability": None,
                "assignments": []
            }
            if "probability" in dest:
                jani_destination["probability"] = JaniExpression(dest["probability"]["exp"])
            if "assignments" in dest:
                for assignment in dest["assignments"]:
                    if isinstance(assignment, dict):
                        jani_destination["assignments"].append(JaniAssignment(assignment))
                    elif isinstance(assignment, JaniAssignment):
                        jani_destination["assignments"].append(assignment)
                    else:
                        raise RuntimeError(f"Unexpected type {type(assignment)} in assignments")
            self.destinations.append(jani_destination)

    def get_action(self) -> Optional[str]:
        """Get the action name, if set."""
        return self.action

    def is_empty_self_loop(self) -> bool:
        """Check if the edge is an empty self loop (i.e. has no assignments)."""
        return len(self.destinations) == 1 and self.location == self.destinations[0]["location"] \
            and len(self.destinations[0]["assignments"]) == 0

    def set_action(self, action_name: str):
        """Set the action name."""
        self.action = action_name

    def as_dict(self, constants: Dict[str, JaniConstant]):
        edge_dict = {
            "location": self.location,
            "destinations": []
        }
        if self.action is not None:
            edge_dict.update({"action": self.action})
        if self.guard is not None:
            extracted_guard = self.guard.as_dict(constants)
            if len(extracted_guard) > 0:
                edge_dict.update({"guard": self.guard.as_dict(constants)})
        for dest in self.destinations:
            single_destination = {
                "location": dest["location"],
            }
            if "probability" in dest:
                if dest["probability"] is not None:
                    prob_exp = expand_expression(dest["probability"], constants)
                    single_destination.update({"probability": {"exp": prob_exp.as_dict()}})
            if "assignments" in dest:
                expanded_assignments = []
                for assignment in dest["assignments"]:
                    expanded_assignments.append(assignment.as_dict(constants))
                single_destination.update({"assignments": expanded_assignments})
            edge_dict["destinations"].append(single_destination)
        return edge_dict
