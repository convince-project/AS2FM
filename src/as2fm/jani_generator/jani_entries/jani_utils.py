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

"""Collection of various utilities for Jani entries."""

from typing import Any, Dict, MutableSequence, Optional, Tuple, Type, get_args

from as2fm.as2fm_common.common import get_default_expression_for_type, is_array_type
from as2fm.jani_generator.jani_entries import JaniAutomaton


def get_variable_type(jani_automaton: JaniAutomaton, variable_name: Optional[str]) -> type:
    """
    Retrieve the variable type from the Jani automaton.

    :param jani_automaton: The Jani automaton to check the variable in.
    :param variable_name: The name of the variable to check.
    :return: The retrieved type.
    """
    assert variable_name is not None, "Variable name must be provided."
    variable = jani_automaton.get_variables().get(variable_name)
    assert (
        variable is not None
    ), f"Variable {variable_name} not found in {jani_automaton.get_variables()}."
    return variable.get_type()


def is_variable_array(jani_automaton: JaniAutomaton, variable_name: Optional[str]) -> bool:
    """Check if a variable is an array.

    :param jani_automaton: The Jani automaton to check the variable in.
    :param variable_name: The name of the variable to check.
    :return: True if the variable is an array, False otherwise.
    """
    return is_array_type(get_variable_type(jani_automaton, variable_name))


def get_array_type_and_size(jani_automaton: JaniAutomaton, var_name: str) -> Tuple[Type, int]:
    """
    Generate the ArrayInfo obj. related to the provided variable.

    :param jani_automaton: The Jani automaton to get the variable from.
    :param var_name: The name of the variable to generate the info from.
    :return: The ArrayInfo obj. with array type and max size.
    """
    assert var_name is not None, "Variable name must be provided."
    variable = jani_automaton.get_variables().get(var_name)
    var_type = variable.get_type()
    assert is_array_type(var_type), f"Variable {var_name} not an array, cannot extract array info."
    array_type = get_args(var_type)[0]
    assert array_type in (int, float), f"Array type {array_type} not supported."
    init_operator = variable.get_init_expr().as_operator()
    assert init_operator is not None, f"Expected init expr of {var_name} to be an operator expr."
    if init_operator[0] == "av":
        max_size = len(init_operator[1]["elements"].as_literal().value())
    elif init_operator[0] == "ac":
        max_size = init_operator[1]["length"].as_literal().value()
    else:
        raise ValueError(f"Unexpected operator {init_operator[0]} for {var_name} init expr.")
    return (array_type, max_size)


def get_all_variables_and_instantiations(jani_automaton: JaniAutomaton) -> Dict[str, Any]:
    """
    Retrieve all variables and their instantiations from the Jani automaton.

    :param jani_automaton: The Jani automaton to retrieve the variables from.
    :return: A dictionary mapping each variable to a dummy value
    """
    variables: Dict[str, Any] = {}
    for n, v in jani_automaton.get_variables().items():
        variables[n] = get_default_expression_for_type(v.get_type())
        # Hack to solve issue for expressions with explicit access to array entries
        if isinstance(variables[n], MutableSequence):
            for _ in range(50):
                variables[n].append(0)
        # Another hack, since javascript interprets 0.0 as int...
        if isinstance(variables[n], float):
            variables[n] = 0.1
    return variables
