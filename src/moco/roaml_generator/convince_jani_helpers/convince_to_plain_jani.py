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

"""
Module to convert convince-flavored robotic, specific jani into plain jani.
"""

import json
from math import degrees
from os import path
from typing import List

from moco.roaml_generator.jani_entries import (
    JaniAutomaton,
    JaniComposition,
    JaniModel,
    JaniProperty,
)


def to_cm(value: float) -> int:
    """Convert meters (float) to cm (int)"""
    return int(value * 100)


def to_deg(value: float) -> int:
    """Convert radians (float) to degrees (int)"""
    return int(degrees(value))


def __convince_env_model_to_jani(base_model: JaniModel, env_model: dict):
    """Add the converted entries from the convince environment model to the provided JaniModel."""
    # Check if the base_model is a JaniModel instance
    assert isinstance(base_model, JaniModel), "The base_model should be a JaniModel instance"
    # Check if the env_model is a dictionary
    assert isinstance(env_model, dict), "The env_model should be a dictionary"
    # Check if the env_model has the required keys
    assert "robots" in env_model, "The env_model should contain the key 'robots'"
    assert "boundaries" in env_model, "The env_model should contain the key 'boundaries'"
    assert "sim_step" in env_model, "The env_model should contain the key 'sim_step'"
    base_model.add_constant("sim_step", float, float(env_model["sim_step"]))
    # Extract the boundaries from the env_model
    boundaries = env_model["boundaries"]
    base_model.add_constant("boundaries.count", int, len(boundaries))
    for idx, boundary in enumerate(boundaries):
        base_model.add_constant(f"boundaries.{idx}.x", float, float(boundary["x"]))
        base_model.add_constant(f"boundaries.{idx}.y", float, float(boundary["y"]))
    # Extract the robots from the env_model
    robots = env_model["robots"]
    for robot in robots:
        robot_name = robot["name"]
        robot_pose = robot["pose"]
        # The robot pose should be stored using integers -> centimeters and degrees
        base_model.add_variable(f"robots.{robot_name}.pose.x_cm", int, to_cm(robot_pose["x"]))
        base_model.add_variable(f"robots.{robot_name}.pose.y_cm", int, to_cm(robot_pose["y"]))
        base_model.add_variable(
            f"robots.{robot_name}.pose.theta_deg", int, to_deg(robot_pose["theta"])
        )
        base_model.add_variable(f"robots.{robot_name}.pose.x", float, transient=True)
        base_model.add_variable(f"robots.{robot_name}.pose.y", float, transient=True)
        base_model.add_variable(f"robots.{robot_name}.pose.theta", float, transient=True)
        base_model.add_variable(f"robots.{robot_name}.goal.x", float, transient=True)
        base_model.add_variable(f"robots.{robot_name}.goal.y", float, transient=True)
        base_model.add_variable(f"robots.{robot_name}.goal.theta", float, transient=True)
        robot_shape = robot["shape"]
        base_model.add_constant(
            f"robots.{robot_name}.shape.radius", float, float(robot_shape["radius"])
        )
        base_model.add_constant(
            f"robots.{robot_name}.shape.height", float, float(robot_shape["height"])
        )
        base_model.add_constant(
            f"robots.{robot_name}.linear_velocity", float, float(robot["linear_velocity"])
        )
        base_model.add_constant(
            f"robots.{robot_name}.angular_velocity", float, float(robot["angular_velocity"])
        )
    if "obstacles" in env_model:
        # Extract the obstacles from the env_model
        # TODO
        pass
    # TODO: Discuss the perception part
    # TODO: Discuss the possibility of generating a base automata for each robot + standard edges
    # (i.e. switch_on/off, drive, rotate)
    # This would make sense, allowing the definition of default mobile robots without the need of
    # defining how they drive.
    # By the way, keeping this out for now!


def __convince_automata_to_jani(base_model: JaniModel, automata_list: List[dict]):
    # Check if the base_model is a JaniModel instance
    assert isinstance(base_model, JaniModel), "The base_model should be a JaniModel instance"
    # Check if the provided automata are in a list
    assert isinstance(automata_list, list), "The env_model should be a dictionary"
    for automaton_dict in automata_list:
        assert isinstance(automaton_dict, dict), "The automata list should contain dictionaries"
        base_model.add_jani_automaton(JaniAutomaton(automaton_dict=automaton_dict))


def __convince_system_to_jani(base_model: JaniModel, system_dict: dict):
    # Check if the base_model is a JaniModel instance
    assert isinstance(base_model, JaniModel), "The base_model should be a JaniModel instance"
    base_model.add_system_sync(JaniComposition(system_dict))


def __convince_properties_to_jani(base_model: JaniModel, properties: List[dict]):
    # Check if the base_model is a JaniModel instance
    assert isinstance(base_model, JaniModel), "The base_model should be a JaniModel instance"
    for property_dict in properties:
        assert isinstance(property_dict, dict), "The properties list should contain dictionaries"
        base_model.add_jani_property(
            JaniProperty(property_dict["name"], property_dict["expression"])
        )


def convince_jani_parser(base_model: JaniModel, convince_jani_path: str): # TODO: Remove this function
    """Read a convince-jani file and add it to a JaniModel object."""
    # Check if the jani_model is a JaniModel instance
    assert isinstance(base_model, JaniModel), "The jani_model should be a JaniModel instance"
    # Check if the convince_jani_path is a file
    assert path.isfile(convince_jani_path), "The convince_jani_path should be a file"
    # Read the convince-jani file
    with open(convince_jani_path, "r", encoding="utf-8") as file:
        convince_jani_json = json.load(file)
    # ---- Metadata ----
    base_model.set_name(convince_jani_json["name"])
    # Make sure we are loading a convince-jani file
    assert (
        "features" in convince_jani_json and "convince_extensions" in convince_jani_json["features"]
    ), "The provided file is not a convince-jani file (missing feature entry)"
    # Extract the environment model from the convince-jani file
    # ---- Environment Model ----
    __convince_env_model_to_jani(base_model, convince_jani_json["rob_env_model"])
    # ---- Automata ----
    __convince_automata_to_jani(base_model, convince_jani_json["automata"])
    # ---- System (Automata composition) ----
    __convince_system_to_jani(base_model, convince_jani_json["system"])
    # ---- Properties ----
    __convince_properties_to_jani(base_model, convince_jani_json["properties"])
