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

from typing import Any, Dict, List, Optional

from moco.roaml_generator.jani_entries import (
    JaniAssignment,
    JaniConstant,
    JaniExpression,
    JaniGuard,
)
from moco.roaml_generator.jani_entries.jani_convince_expression_expansion import expand_expression


class JaniEdge:
    def __init__(self, edge_dict: dict):
        self.location = edge_dict["location"]
        self.action: Optional[str] = None
        if "action" in edge_dict:
            self.action = edge_dict["action"]
        self.guard = None
        if "guard" in edge_dict:
            self.guard = JaniGuard(edge_dict["guard"])
        self.destinations: List[Dict[str, Any]] = []
        if "destinations" not in edge_dict:
            return
        for dest in edge_dict["destinations"]:
            prob = None
            if "probability" in dest:
                prob = JaniExpression(dest["probability"]["exp"])
            assignments = []
            if "assignments" in dest:
                for assignment in dest["assignments"]:
                    if isinstance(assignment, dict):
                        assignments.append(JaniAssignment(assignment))
                    elif isinstance(assignment, JaniAssignment):
                        assignments.append(assignment)
                    else:
                        raise RuntimeError(f"Unexpected type {type(assignment)} in assignments")
            self.append_destination(
                location=dest["location"], probability=prob, assignments=assignments
            )

    def get_action(self) -> Optional[str]:
        """Get the action name, if set."""
        return self.action

    def append_destination(
        self,
        *,
        location: Optional[str] = None,
        probability: Optional[JaniExpression] = None,
        assignments: Optional[List[JaniAssignment]] = None,
    ):
        """
        Add a new destination to the JaniEdge.
        """
        assert location is None or isinstance(location, str)
        assert probability is None or isinstance(probability, JaniExpression)
        assert assignments is None or all(
            isinstance(assign, JaniAssignment) for assign in assignments
        )
        jani_destination = {
            "location": location,
            "probability": probability,
            "assignments": [] if assignments is None else assignments,
        }
        self.destinations.append(jani_destination)

    def is_empty_self_loop(self) -> bool:
        """Check if the edge is an empty self loop (i.e. has no assignments)."""
        return (
            len(self.destinations) == 1
            and self.location == self.destinations[0]["location"]
            and len(self.destinations[0]["assignments"]) == 0
        )

    def set_action(self, action_name: str):
        """Set the action name."""
        self.action = action_name

    def as_dict(self, constants: Dict[str, JaniConstant]):
        edge_dict = {"location": self.location, "destinations": []}
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


def _sort_assignments_by_index(assignments: List[JaniAssignment]) -> None:
    """Sorts a list of assignments by assignment index."""
    assignments.sort(key=lambda assignment: assignment.get_index())
