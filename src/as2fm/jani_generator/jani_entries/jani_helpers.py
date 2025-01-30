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

from typing import List, Union

from as2fm.jani_generator.jani_entries import JaniAssignment, JaniEdge, JaniExpression, JaniModel
from as2fm.jani_generator.jani_entries.jani_convince_expression_expansion import (
    expand_distribution_expressions,
)


def _generate_new_edge_for_random_assignments(
    edge_location: str,
    edge_target: str,
    assignment_var: Union[str, JaniExpression],
    assignment_possibilities: List[JaniExpression],
) -> JaniEdge:
    probability = 1.0 / len(assignment_possibilities)
    return JaniEdge(
        {
            "location": edge_location,
            "destinations": [
                {
                    "location": edge_target,
                    "probability": {"exp": probability},
                    "assignments": [{"ref": assignment_var, "value": assignment_value}],
                }
                for assignment_value in assignment_possibilities
            ],
        }
    )


def _expand_random_variables_in_edge(jani_edge: JaniEdge, *, n_options: int) -> List[JaniEdge]:
    """
    If there are random variables in the input JaniEdge, generate new edges to handle it.

    :param jani_edge: The edge to expand
    :return: All the edges resulting from the input.
    """
    generated_edges: List[JaniEdge] = [jani_edge]
    edge_location = jani_edge.location
    edge_action = jani_edge.action
    assert edge_action is not None, "Expected edge actions to be always defined."
    edge_id = f"{edge_location}_{edge_action}"

    for dest_id, dest_val in enumerate(jani_edge.destinations):
        jani_assignments: List[JaniAssignment] = dest_val["assignments"]
        curr_assign_idx = 0
        while curr_assign_idx < len(jani_assignments):
            expanded_assignments = expand_distribution_expressions(
                jani_assignments[curr_assign_idx].get_expression(), n_options=n_options
            )
            if len(expanded_assignments) > 1:
                # In this case, we expanded the assignments, and we need to generate new edges
                original_target_loc = dest_val["location"]
                expanded_edge_loc = f"{edge_id}_dest_{dest_id}_expanded_assign_{curr_assign_idx}"
                next_target_edge_loc = f"{edge_id}_dest_{dest_id}_after_assign_{curr_assign_idx}"
                expanded_edge = _generate_new_edge_for_random_assignments(
                    expanded_edge_loc,
                    next_target_edge_loc,
                    jani_assignments[curr_assign_idx].get_target(),
                    expanded_assignments,
                )
                next_assign_idx = curr_assign_idx + 1
                continuation_edge = JaniEdge(
                    {
                        "location": next_target_edge_loc,
                        "action": "act",  # Keep it simple, due to the location naming scheme
                        "destinations": [
                            {
                                "location": original_target_loc,
                                "assignments": jani_assignments[next_assign_idx:],
                            }
                        ],
                    }
                )
                dest_val["location"] = expanded_edge_loc
                dest_val["assignments"] = dest_val["assignments"][0:curr_assign_idx]
                generated_edges.append(expanded_edge)
                generated_edges.extend(
                    _expand_random_variables_in_edge(continuation_edge, n_options=n_options)
                )
                break
            curr_assign_idx += 1
    return generated_edges


def expand_random_variables_in_jani_model(model: JaniModel, *, n_options: int) -> None:
    """Find all expression containing the 'distribution' expression and expand them."""
    # Check that no global variable has a random value (not supported)
    for g_var_name, g_var in model.get_variables().items():
        assert (
            len(expand_distribution_expressions(g_var.get_init_expr())) == 1
        ), f"Global variable {g_var_name} is init using a random value. This is unsupported."
    for automaton in model.get_automata():
        # Also for automaton, check variables initialization
        for aut_var_name, aut_var in automaton.get_variables().items():
            assert len(expand_distribution_expressions(aut_var.get_init_expr())) == 1, (
                f"Variable {aut_var_name} in automaton {automaton.get_name()} is init using random "
                f"values: init expr = '{aut_var.get_init_expr().as_dict()}'. This is unsupported."
            )
        # Edges created to handle random distributions
        new_edges: List[JaniEdge] = []
        for edge in automaton.get_edges():
            generated_edges = _expand_random_variables_in_edge(edge, n_options=n_options)
            for gen_edge in generated_edges:
                automaton.add_location(gen_edge.location)
            new_edges.extend(generated_edges)
        automaton.set_edges(new_edges)
    model._generate_missing_syncs()
