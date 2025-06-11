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


from typing import Any, Dict, Optional

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
        self._values: PropertyEntry = ProbabilityProperty(prop_values)
        if self._values.is_valid():
            return
        self._values = RewardProperty(prop_values)
        if self._values.is_valid():
            return
        self._values = NumPathsProperty(prop_values)
        assert self._values.is_valid(), "Unexpected values in FilterProperty"

    def get_property_operands(self) -> Dict[str, JaniExpression]:
        return self._values.get_exp_operands()

    def as_dict(self, constants: Dict[str, JaniConstant]):
        assert isinstance(
            self._values, ProbabilityProperty
        ), "Only ProbabilityProperty is supported in FilterProperty"
        return {
            "op": "filter",
            "fun": self._fun,
            "values": self._values.as_dict(constants),
            "states": {"op": "initial"},
        }


class PropertyEntry:
    """Generic entry that must be contained in the PropertyFilter class."""

    def __init__(self):
        self._op = None
        self._exp = None
        self._valid = False

    def is_valid(self) -> bool:
        return self._valid

    def get_op(self):
        return self._op

    def get_exp(self):
        return self._exp

    def get_exp_operands(self) -> Dict[str, JaniExpression]:
        raise NotImplementedError(f"Class {type(self)} does not implement 'get_exp_operands'")


class ProbabilityProperty(PropertyEntry):
    """Pmin / Pmax"""

    def __init__(self, prop_values: Dict[str, Any]):
        super().__init__()
        if "op" in prop_values and "exp" in prop_values:
            if prop_values["op"] in ("Pmin", "Pmax"):
                self._op = prop_values["op"]
                self._exp = PathProperty(prop_values["exp"])
                self._valid = self._exp.is_valid()

    def get_exp_operands(self) -> Dict[str, JaniExpression]:
        return self._exp.get_operands()

    def as_dict(self, constants: Dict[str, JaniConstant]):
        return {"op": self._op, "exp": self._exp.as_dict(constants)}


class RewardProperty(PropertyEntry):
    """E properties"""

    def __init__(self, prop_values: Dict[str, Any]):
        super().__init__()


class NumPathsProperty(PropertyEntry):
    """This address properties where we want the property verified on all / at least one case."""

    def __init__(self, prop_values: Dict[str, Any]):
        super().__init__()


class PathProperty:
    """Mainly Until properties. Need to check support of Next and Global properties in Jani."""

    def __init__(self, prop_values: Dict[str, Any]):
        self._valid = False
        self._comment: Optional[str] = prop_values.get("comment")
        self._op: Optional[str] = prop_values.get("op")
        if self._op is None:
            return
        self._operands: Dict[str, JaniExpression] = {}
        if self._op in ("F", "G"):
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

    def get_operands(self) -> Dict[str, JaniExpression]:
        """Return the reference to the property operands."""
        return self._operands

    def as_dict(self, constants: Dict[str, JaniConstant]):
        ret_dict = {}
        if self._comment is not None:
            ret_dict.update({"comment": self._comment})
        ret_dict.update({"op": self._op})
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
        self._expression = FilterProperty(expression)

    def get_property_operands(self) -> Dict[str, JaniExpression]:
        """Get the expressions defined in the property (as LTL property operands)."""
        return self._expression.get_property_operands()

    def as_dict(self, constants: Dict[str, JaniConstant]):
        return {"name": self._name, "expression": self._expression.as_dict(constants)}
