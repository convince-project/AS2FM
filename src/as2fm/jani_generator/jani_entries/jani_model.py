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
Complete Jani Model
"""


from typing import Dict, List, Optional, Type, Union

from as2fm.as2fm_common.array_type import ArrayInfo
from as2fm.jani_generator.jani_entries import (
    JaniAutomaton,
    JaniComposition,
    JaniConstant,
    JaniExpression,
    JaniProperty,
    JaniValue,
    JaniVariable,
)

ValidValue = Union[int, float, bool, dict, JaniExpression]


class JaniModel: # TODO: Remove this class
    """
    Class representing a complete Jani Model, containing all necessary information to generate
    a plain Jani file.
    """

    @staticmethod
    def from_dict(model_dict: dict) -> "JaniModel":
        model = JaniModel()
        model.set_name(model_dict["name"])
        for feature in model_dict.get("features", []):
            model.add_feature(feature)
        for variable_dict in model_dict["variables"]:
            model.add_jani_variable(JaniVariable.from_dict(variable_dict))
        for constant_dict in model_dict["constants"]:
            model.add_jani_constant(JaniConstant.from_dict(constant_dict))
        for automaton_dict in model_dict["automata"]:
            model.add_jani_automaton(JaniAutomaton.from_dict(automaton_dict))
        model.add_system_sync(JaniComposition.from_dict(model_dict["system"]))
        for property_dict in model_dict["properties"]:
            model.add_jani_property(JaniProperty.from_dict(property_dict))
        return model

    def __init__(self):
        self._name = ""
        self._type = "mdp"
        self._features: List[str] = []
        self._variables: Dict[str, JaniVariable] = {}
        self._constants: Dict[str, JaniConstant] = {}
        self._automata: List[JaniAutomaton] = []
        # The list of actions can be generated later on from the automata
        self._system: Optional[JaniComposition] = None
        self._properties: List[JaniProperty] = []

    def set_name(self, name: str):
        self._name = name

    def get_name(self):
        return self._name

    def add_feature(self, feature: str):
        assert feature in ["arrays", "trigonometric-functions"], f"Unknown Jani feature {feature}"
        self._features.append(feature)

    def get_features(self) -> List[str]:
        return self._features

    def add_jani_variable(self, variable: JaniVariable):
        self._variables.update({variable.name(): variable})

    def add_jani_variables(self, variables: List[JaniVariable]):
        for jani_var in variables:
            self.add_jani_variable(jani_var)

    def add_variable(
        self,
        variable_name: str,
        variable_type: Type,
        variable_init_expression: Optional[ValidValue] = None,
        transient: bool = False,
        array_info: Optional[ArrayInfo] = None,
    ):
        if variable_init_expression is None or isinstance(variable_init_expression, JaniExpression):
            self.add_jani_variable(
                JaniVariable(
                    variable_name, variable_type, variable_init_expression, transient, array_info
                )
            )
        else:
            assert JaniValue(
                variable_init_expression
            ).is_valid(), f"Invalid value for variable {variable_name}"
            self.add_jani_variable(
                JaniVariable(
                    variable_name,
                    variable_type,
                    JaniExpression(variable_init_expression),
                    transient,
                    array_info,
                )
            )

    def add_jani_constant(self, constant: JaniConstant):
        self._constants.update({constant.name(): constant})

    def add_constant(self, constant_name: str, constant_type: Type, constant_value: ValidValue):
        if isinstance(constant_value, JaniExpression):
            self.add_jani_constant(JaniConstant(constant_name, constant_type, constant_value))
        else:
            assert JaniValue(
                constant_value
            ).is_valid(), f"Invalid value for constant {constant_name}"
            self.add_jani_constant(
                JaniConstant(constant_name, constant_type, JaniExpression(constant_value))
            )

    def add_jani_automaton(self, automaton: JaniAutomaton):
        self._automata.append(automaton)

    def get_automata(self) -> List[JaniAutomaton]:
        return self._automata

    def get_constants(self) -> Dict[str, JaniConstant]:
        return self._constants

    def get_variables(self) -> Dict[str, JaniVariable]:
        return self._variables

    def get_automaton(self, automaton_name: str) -> Optional[JaniAutomaton]:
        for automaton in self._automata:
            if automaton._name == automaton_name:
                return automaton
        return None

    def add_system_sync(self, system: JaniComposition):
        """Specify how the different automata are composed together."""
        self._system = system
        self._generate_missing_syncs()

    def remove_edges_with_action(self, action: str):
        """Remove the edges in all automaton with the action name provided.

        :param action: The name of the action to remove.
        """
        assert isinstance(action, str), "Action name must be a string"
        for automaton in self._automata:
            automaton.remove_edges_with_action_name(action)

    def _generate_missing_syncs(self):
        """Automatically generate the syncs that are not explicitly defined."""
        assert len(self._automata) == len(
            self._system.get_elements()
        ), "We expect there to be explicit syncs for all automata."
        for automaton in self._automata:
            existing_syncs = self._system.get_syncs_for_element(automaton.get_name())
            for action in automaton.get_actions():
                if action not in existing_syncs:
                    self._system.add_sync(action, {automaton.get_name(): action})

    def add_jani_property(self, property: JaniProperty):
        """Add a single property to the model."""
        self._properties.append(property)

    def get_properties(self) -> List[JaniProperty]:
        """Get all the properties in the model."""
        return self._properties

    def as_dict(self):
        assert self._system is not None, "The system composition is not set"
        model_dict = {}
        # The available actions need to be stored explicitly in jani:
        # we extract them from all the automaton in the model
        available_actions = set()
        for automaton in self._automata:
            available_actions.update(automaton.get_actions())
        model_dict.update(
            {
                "jani-version": 1,
                "name": self._name,
                "type": self._type,
                "features": self._features,
                "metadata": {
                    "description": "Autogenerated with CONVINCE toolchain",
                },
                "variables": [
                    jani_variable.as_dict() for jani_variable in self._variables.values()
                ],
                "constants": [
                    jani_constant.as_dict() for jani_constant in self._constants.values()
                ],
                "actions": [{"name": action} for action in sorted(list(available_actions))],
                "automata": [
                    jani_automaton.as_dict(self._constants) for jani_automaton in self._automata
                ],
                "system": self._system.as_dict(),
                "properties": [
                    jani_property.as_dict(self._constants) for jani_property in self._properties
                ],
            }
        )
        return model_dict
