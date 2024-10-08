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
Properties in Jani
"""


from typing import Any, Dict, Union

from as2fm.jani_generator.jani_entries import JaniConstant, JaniExpression
from as2fm.jani_generator.jani_entries.jani_convince_expression_expansion import expand_expression


class FilterProperty:
    """All Property operators must occur in a FilterProperty object."""

    def __init__(self, property_filter_exp: Dict[str, Any]):
        assert isinstance(property_filter_exp, dict), "Unexpected FilterProperty initialization"
        assert (
            "op" in property_filter_exp and property_filter_exp["op"] == "filter"
        ), "Unexpected FilterProperty initialization"
        self._fun = property_filter_exp["fun"]
        raw_states = property_filter_exp["states"]
        assert isinstance(raw_states, dict) and raw_states["op"] == "initial"
        self._process_values(property_filter_exp["values"])

    def _process_values(self, prop_values: Dict[str, Any]) -> None:
        self._values: Union[ProbabilityProperty, RewardProperty, NumPathsProperty] = (
            ProbabilityProperty(prop_values)
        )
        if self._values.is_valid():
            return
        self._values = RewardProperty(prop_values)
        if self._values.is_valid():
            return
        self._values = NumPathsProperty(prop_values)
        assert self._values.is_valid(), "Unexpected values in FilterProperty"

    def as_dict(self, constants: Dict[str, JaniConstant]):
        assert isinstance(
            self._values, ProbabilityProperty
        ), "Only ProbabilityProperty is supported in FilterProperty"
        return {
            "op": "filter",
            "fun": self._fun,
            "states": {"op": "initial"},
            "values": self._values.as_dict(constants),
        }


class ProbabilityProperty:
    """Pmin / Pmax"""

    def __init__(self, prop_values: Dict[str, Any]):
        self._valid = False
        if "op" in prop_values and "exp" in prop_values:
            if prop_values["op"] in ("Pmin", "Pmax"):
                self._op = prop_values["op"]
                self._exp = PathProperty(prop_values["exp"])
                self._valid = self._exp.is_valid()

    def is_valid(self) -> bool:
        return self._valid

    def as_dict(self, constants: Dict[str, JaniConstant]):
        return {"op": self._op, "exp": self._exp.as_dict(constants)}


class RewardProperty:
    """E properties"""

    def __init__(self, prop_values: Dict[str, Any]):
        self._valid = False

    def is_valid(self) -> bool:
        return self._valid


class NumPathsProperty:
    """This address properties where we want the property verified on all / at least one case."""

    def __init__(self, prop_values: Dict[str, Any]):
        self._valid = False

    def is_valid(self) -> bool:
        return self._valid


class PathProperty:
    """Mainly Until properties. Need to check support of Next and Global properties in Jani."""

    def __init__(self, prop_values: Dict[str, Any]):
        self._valid = False
        if "op" not in prop_values:
            return
        self._op: str = prop_values["op"]
        self._operands: Dict[str, JaniExpression] = {}
        if self._op == "F":
            self._operands = {"exp": JaniExpression(prop_values["exp"])}
        elif self._op in ("U", "W"):
            self._operands = {
                "left": JaniExpression(prop_values["left"]),
                "right": JaniExpression(prop_values["right"]),
            }
        else:
            print(f"Warning: Unsupported PathProperty operator {self._op}")
            return
        self._bounds = None
        if "step-bounds" in prop_values:
            self._bounds = PathPropertyStepBounds(prop_values["step-bounds"])
            if not self._bounds.is_valid():
                print("Warning: Invalid step-bounds in PathProperty")
                self._bounds = None
        self._valid = True

    def is_valid(self) -> bool:
        return self._valid

    def as_dict(self, constants: Dict[str, JaniConstant]):
        ret_dict = {"op": self._op}
        ret_dict.update(
            {
                operand: expand_expression(expr, constants).as_dict()
                for operand, expr in self._operands.items()
            }
        )
        if self._bounds is not None:
            ret_dict["step-bounds"] = self._bounds.as_dict(constants)
        return ret_dict


class PathPropertyStepBounds:
    def __init__(self, bound_values: Dict[str, Any]):
        self._lower_bound = None
        self._upper_bound = None
        if "lower" in bound_values:
            self._lower_bound = JaniExpression(bound_values["lower"])
        if "upper" in bound_values:
            self._upper_bound = JaniExpression(bound_values["upper"])
        self._valid = self._lower_bound is not None or self._upper_bound is not None

    def is_valid(self) -> bool:
        return self._valid

    def as_dict(self, constants: Dict[str, JaniConstant]):
        if not self._valid:
            return None
        ret_dict = {}
        if self._lower_bound is not None:
            ret_dict["lower"] = expand_expression(self._lower_bound, constants).as_dict()
        if self._upper_bound is not None:
            ret_dict["upper"] = expand_expression(self._upper_bound, constants).as_dict()
        return ret_dict


class JaniProperty:
    @staticmethod
    def from_dict(property_dict: dict) -> "JaniProperty":
        return JaniProperty(property_dict["name"], property_dict["expression"])

    def __init__(self, name, expression):
        self._name = name
        # TODO: For now copy as it is. Later we might expand it to support more functionalities
        self._expression = FilterProperty(expression)

    def as_dict(self, constants: Dict[str, JaniConstant]):
        return {"name": self._name, "expression": self._expression.as_dict(constants)}
