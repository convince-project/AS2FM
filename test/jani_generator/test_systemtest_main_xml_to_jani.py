# Copyright (c) 2025 - for information on the respective copyright owner
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

"""Test the conversion from a main.xml to JANI and running it with SMC Storm."""

import os

import pytest

from as2fm.jani_generator.scxml_helpers.top_level_interpreter import (
    interpret_top_level_xml,
    parse_main_xml,
)

from ..as2fm_common.test_utilities_smc_storm import run_smc_storm_with_output
from .utils import json_jani_properties_match

rel_examples_folder = os.path.join("..", "..", "..", "examples")

PROB_ERROR_TOLERANCE = 0.015


# pylint: disable=too-many-arguments, too-many-positional-arguments
def _test_with_main(
    folder: str,
    property_name: str,
    expected_result_probability: float,
    model_xml: str,
    generate_plain_scxml: bool,
    skip_smc: bool,
    result_probability_tolerance: float,
    trace_length_limit: int,
    n_traces_limit: int,
    skip_properties_load_check: bool,
    disable_cache: bool,
    n_threads: int,
    batch_size: int,
    _case_name: str,
):
    """
    Testing the conversion of the model xml file with the entrypoint.

    :param folder: The folder containing the test data.
    :param model_xml: the name of the xml file containing the model to evaluate.
    :param generate_plain_scxml: If the plain SCXMLs should be generated.
    :param skip_smc: If the model shall be executed using SMC (uses smc_storm).
    :param property_name: The property name to test.
    :param expected_result_probability: The expected probability the prop. is verified from SMC.
    :param result_probability_tolerance: The allowed error for the prob. result.
    :param trace_length_limit: the max length a single trace can reach
    :param n_traces_limit: The max. number of iterations to run in SMC.
    :param skip_properties_load_check: Disable the equality check for the loaded properties.
    :param disable_cache: Whether to disable cache in smc_storm.
    :param n_threads: How many threads to use.
    :param batch_size: How many traces to compute in a batch before checking for convergence.
    :param _case_name: Unused here. Needed to name the parameterized tests.
    """
    test_data_dir = os.path.join(os.path.dirname(__file__), "_test_data", folder)
    xml_main_path = os.path.join(test_data_dir, model_xml)
    assert xml_main_path.endswith(".xml"), f"Unexpected format of main xml file {xml_main_path}"
    model_jani = model_xml.removesuffix("xml") + "jani"
    jani_path = os.path.join(test_data_dir, model_jani)
    if os.path.exists(jani_path):
        os.remove(jani_path)
    generated_scxml_path = "generated_plain_scxml" if generate_plain_scxml else None

    if generate_plain_scxml:
        plain_scxml_path = os.path.join(test_data_dir, "generated_plain_scxml")

    try:
        interpret_top_level_xml(
            xml_main_path, jani_file=model_jani, scxmls_dir=generated_scxml_path
        )
        if generate_plain_scxml:
            assert os.path.exists(plain_scxml_path)
            generated_files = os.listdir(plain_scxml_path)
            # Ensure there is the data type comment in the generated SCXML
            assert len(generated_files) > 0, "Expected at least one gen. SCXML file."
            for file in os.listdir(plain_scxml_path):
                with open(os.path.join(plain_scxml_path, file), "r", encoding="utf-8") as f:
                    # Make sure that the generated plain SCXML files use the agreed format
                    content = f.read()
                    if "<datamodel>" in content:
                        assert "<!-- TYPE" in content
                    if "<send" in content:
                        assert "target=" in content
        assert os.path.exists(jani_path)
        properties_file = os.path.join(test_data_dir, parse_main_xml(xml_main_path).properties[0])
        if not skip_properties_load_check:
            assert json_jani_properties_match(
                properties_file, jani_path
            ), "Properties from input json and generated jani file do not match."
        if not skip_smc:
            assert len(property_name) > 0, "Property name must be provided for SMC."
            storm_args = (
                f"--model {jani_path} --properties-names {property_name} "
                + f"--max-trace-length {trace_length_limit} --max-n-traces {n_traces_limit} "
                + f"--n-threads {n_threads} --batch-size {batch_size} --hide-progress-bar"
            )
            if disable_cache:
                storm_args += " --disable-explored-states-caching"
            run_smc_storm_with_output(
                storm_args,
                [property_name, jani_path],
                [],
                expected_result_probability,
                result_probability_tolerance,
            )
    finally:
        # cleanup
        if os.path.exists(jani_path):
            os.remove(jani_path)
        if generate_plain_scxml:
            for file in os.listdir(plain_scxml_path):
                os.remove(os.path.join(plain_scxml_path, file))
            os.removedirs(plain_scxml_path)


def _default_case():
    return {
        "_case_name": "TBD",
        "folder": None,
        "property_name": None,
        "expected_result_probability": 1.0,
        "model_xml": "main.xml",
        "generate_plain_scxml": True,
        "skip_smc": False,
        "result_probability_tolerance": 0.0,
        "trace_length_limit": 10_000,
        "n_traces_limit": 10_000,
        "skip_properties_load_check": False,
        "disable_cache": False,
        "n_threads": 1,
        "batch_size": 100,
    }


def get_cases():
    return [
        # -------------------------------------------------------------------------------------
        # Basic examples
        # Test the battery_depleted property is satisfied.
        _default_case()
        | {
            "_case_name": "battery_ros_example_depleted_success",
            "folder": "ros_example",
            "property_name": "battery_depleted",
        },
        # Expect the property to be *not* satisfied.
        _default_case()
        | {
            "_case_name": "battery_ros_example_over_depleted_fail",
            "folder": "ros_example",
            "property_name": "battery_over_depleted",
            "expected_result_probability": 0.0,
        },
        # Test the alarm turns on before the battery level gets below 28%.
        _default_case()
        | {
            "_case_name": "battery_ros_example_alarm_on",
            "folder": "ros_example",
            "property_name": "alarm_on",
        },
        # Expect the property to be *not* satisfied.
        # TODO: Improve properties under evaluation!
        _default_case()
        | {
            "_case_name": "battery_ros_example_alarm_on",
            "folder": os.path.join(rel_examples_folder, "quick_start_battery_monitor"),
            "property_name": "battery_depleted",
            "expected_result_probability": 0.0,
        },
        # Expect the property to be *not* satisfied.
        # TODO: Improve properties under evaluation!
        _default_case()
        | {
            "_case_name": "battery_monitor_depleted",
            "folder": os.path.join(rel_examples_folder, "quick_start_battery_monitor"),
            "property_name": "battery_depleted",
            "expected_result_probability": 0.0,
        },
        # Expect the property to be *not* satisfied.
        # TODO: Improve properties under evaluation!
        _default_case()
        | {
            "_case_name": "battery_monitor_below_20",
            "folder": os.path.join(rel_examples_folder, "quick_start_battery_monitor"),
            "property_name": "battery_below_20",
            "expected_result_probability": 0.0,
        },
        # Expect the alarm to be on
        _default_case()
        | {
            "_case_name": "battery_monitor_alarm_on",
            "folder": os.path.join(rel_examples_folder, "quick_start_battery_monitor"),
            "property_name": "battery_alarm_on",
        },
        # Expect the battery to be charged in the end.
        _default_case()
        | {
            "_case_name": "battery_monitor_charged",
            "folder": os.path.join(rel_examples_folder, "quick_start_battery_monitor"),
            "property_name": "battery_charged",
        },
        # -------------------------------------------------------------------------------------
        # HL-SCXML features
        # Test that the synchronization can handle events being sent in different orders
        # without deadlocks.
        _default_case()
        | {
            "_case_name": "events_sync_handling",
            "folder": "events_sync_examples",
            "property_name": "seq_check",
        },
        # Test that multiple rates in the same system are handled fine.
        _default_case()
        | {
            "_case_name": "different_rate_senders",
            "folder": "different_rate_senders",
            "property_name": "counter_check",
        },
        # Test topic synchronization, handling events being sent in different orders
        # without deadlocks.
        _default_case()
        | {
            "_case_name": "multiple_senders_same_event",
            "folder": "multiple_senders_same_event",
            "property_name": "seq_check",
        },
        # Test the execution of onentry and onexit for normal and autogenerated transitions.
        _default_case()
        | {
            "_case_name": "on_entry_exit_test",
            "folder": "on_entry_exit_test",
            "property_name": "working",
        },
        # Test transitions upon same event with multiple conditions.
        _default_case()
        | {
            "_case_name": "conditional_transitions",
            "folder": "conditional_transitions",
            "property_name": "destination_reached",
        },
        # Test the array model.
        _default_case()
        | {
            "_case_name": "array_model_basic",
            "folder": "array_model_basic",
            "property_name": "array_check",
        },
        # Test the array model for complex operations.
        _default_case()
        | {
            "_case_name": "array_model_additional",
            "folder": "array_model_additional",
            "property_name": "array_check",
        },
        # Test the array model with multiple dimensions.
        _default_case()
        | {
            "_case_name": "array_model_multi_dim",
            "folder": "array_model_multi_dim",
            "property_name": "array_check",
        },
        # Probabilistic transitions.
        _default_case()
        | {
            "_case_name": "probabilistic_transitions",
            "folder": "probabilistic_transitions",
            "property_name": "expected_counts",
            "result_probability_tolerance": PROB_ERROR_TOLERANCE,
            "n_threads": 8,
            "trace_length_limit": 20_000,
        },
        # -------------------------------------------------------------------------------------
        # Custom data structs
        # XML struct definitions
        _default_case()
        | {
            "_case_name": "data_structs_xml",
            "folder": "data_structs",
            "model_xml": "main_xml_def.xml",
            "property_name": "success",
            "disable_cache": True,
        },
        # JSON struct definitions
        _default_case()
        | {
            "_case_name": "data_structs_json",
            "folder": "data_structs",
            "model_xml": "main_json_def.xml",
            "property_name": "success",
            "disable_cache": True,
        },
        # -------------------------------------------------------------------------------------
        # String support
        # Strings are sent and compared correctly.
        _default_case()
        | {
            "_case_name": "string_comparison_two_sent",
            "folder": "string_comparison",
            "property_name": "string_two_sent",
            "expected_result_probability": 0.6,
            "result_probability_tolerance": PROB_ERROR_TOLERANCE,
            "skip_properties_load_check": True,
        },
        # Strings are sent and compared correctly.
        _default_case()
        | {
            "_case_name": "string_comparison_res_one",
            "folder": "string_comparison",
            "property_name": "strings_res_one",
            "expected_result_probability": 0.3,
            "result_probability_tolerance": PROB_ERROR_TOLERANCE,
            "skip_properties_load_check": True,
        },
        # Strings are sent and compared correctly.
        _default_case()
        | {
            "_case_name": "string_comparison_res_two",
            "folder": "string_comparison",
            "property_name": "strings_res_two",
            "expected_result_probability": 0.6,
            "result_probability_tolerance": PROB_ERROR_TOLERANCE,
            "skip_properties_load_check": True,
        },
        # Strings are sent and compared correctly.
        _default_case()
        | {
            "_case_name": "string_comparison_res_min_one",
            "folder": "string_comparison",
            "property_name": "strings_res_min_one",
            "expected_result_probability": 0.1,
            "result_probability_tolerance": PROB_ERROR_TOLERANCE,
            "skip_properties_load_check": True,
        },
        # Arrays of strings
        _default_case()
        | {
            "_case_name": "array_of_strings",
            "folder": "array_of_strings",
            "property_name": "array_check",
        },
        # -------------------------------------------------------------------------------------
        # ROS features
        # Test String types in ROS interfaces works correctly
        _default_case()
        | {
            "_case_name": "ros_topic_with_strings",
            "folder": "string_msg_comparison",
            "property_name": "success",
        },
        # Test services are properly handled in Jani.
        _default_case()
        | {
            "_case_name": "ros_add_int_srv_example",
            "folder": "ros_add_int_srv_example",
            "property_name": "happy_clients",
        },
        # Also in case we are dealing with float numbers
        _default_case()
        | {
            "_case_name": "set_float_srv_example",
            "folder": "set_float_srv_example",
            "property_name": "float_received",
            "disable_cache": True,
        },
        # Test actions are properly handled in Jani.
        _default_case()
        | {
            "_case_name": "fibonacci_action_example",
            "folder": "fibonacci_action_example",
            "property_name": "clients_ok",
        },
        # Test actions with one client are properly handled in Jani.
        _default_case()
        | {
            "_case_name": "fibonacci_action_single_thread",
            "folder": "fibonacci_action_single_thread",
            "property_name": "client1_ok",
        },
        # Nested data in ROS types.
        _default_case()
        | {
            "_case_name": "nested_data_ros",
            "folder": "nested_data_ros",
            "property_name": "success",
        },
        # -------------------------------------------------------------------------------------
        # Behavior Tree features
        # Basic blackboard support.
        _default_case()
        | {
            "_case_name": "blackboard_test",
            "folder": "blackboard_test",
            "property_name": "tree_success",
        },
        # -------------------------------------------------------------------------------------
        # Special Demos
        # Grid robot with blackboard.
        _default_case()
        | {
            "_case_name": "grid_robot_blackboard",
            "folder": "grid_robot_blackboard",
            "property_name": "at_goal",
            "n_threads": 8,
        },
        # Simpler grid robot with blackboard.
        _default_case()
        | {
            "_case_name": "grid_robot_blackboard_simple",
            "folder": "grid_robot_blackboard_simple",
            "property_name": "tree_success",
            "n_threads": 8,
            "trace_length_limit": 1_000_000,
        },
        # The fetch and carry example deterministic version.
        _default_case()
        | {
            "_case_name": "tutorial_fetch_and_carry_deterministic",
            "folder": os.path.join(rel_examples_folder, "tutorial_fetch_and_carry"),
            "property_name": "snack_at_table",
        },
        # The fetch and carry example probabilistic version with retrying.
        _default_case()
        | {
            "_case_name": "tutorial_fetch_and_carry_prob_retry",
            "folder": os.path.join(rel_examples_folder, "tutorial_fetch_and_carry"),
            "property_name": "snack_at_table",
            "model_xml": "main_probabilistic_extended_bt.xml",
            "expected_result_probability": 0.954,
            "result_probability_tolerance": PROB_ERROR_TOLERANCE,
        },
        # Simple robot navigation demo.
        _default_case()
        | {
            "_case_name": "robot_navigation_tutorial",
            "folder": "robot_navigation_tutorial",
            "property_name": "goal_reached",
            "skip_smc": True,
        },
        # Simple robot navigation demo with a behavior tree.
        _default_case()
        | {
            "_case_name": "robot_navigation_with_bt",
            "folder": "robot_navigation_with_bt",
            "property_name": "goal_reached",
            "skip_smc": True,
        },
        # -------------------------------------------------------------------------------------
        # CONVINCE Use Cases
        # UC1 docking BT.
        _default_case()
        | {
            "_case_name": "uc1_docking",
            "folder": "uc1_docking",
            "property_name": "charging_starts",
            "trace_length_limit": 1_000_000,
        },
        # UC1 docking BT (with a bug).
        _default_case()
        | {
            "_case_name": "uc1_docking_bugged",
            "folder": "uc1_docking",
            "model_xml": "main_with_problem.xml",
            "property_name": "charging_starts",
            "expected_result_probability": 0.0,
            "trace_length_limit": 1_000_000,
            "n_threads": 8,
        },
        # UC1 Complete Mission
        _default_case()
        | {
            "_case_name": "uc1_mission",
            "folder": "uc1_mission",
            "model_xml": "main.xml",
            "property_name": "tree_finished_robot_docked",
            "expected_result_probability": 1.0,
            "trace_length_limit": 1_000_000,
            "n_traces_limit": 50,
            "n_threads": 8,
            "batch_size": 1,
        },
        # UC2 Assembly recovery
        _default_case()
        | {
            "_case_name": "uc2_assembly_trigger_recovery",
            "folder": os.path.join("uc2_assembly", "Main"),
            "property_name": "executes_recovery_branch_or_success",
        },
        # UC2 Assembly move success
        _default_case()
        | {
            "_case_name": "uc2_assembly_move_success",
            "folder": os.path.join("uc2_assembly", "Main"),
            "property_name": "move_success",
        },
        # UC2 Assembly with bugged BT.
        _default_case()
        | {
            "_case_name": "uc2_assembly_with_bug",
            "folder": os.path.join("uc2_assembly", "Main"),
            "model_xml": "main_bug.xml",
            "property_name": "executes_recovery_branch_or_success",
            "expected_result_probability": 0.7,
            "result_probability_tolerance": PROB_ERROR_TOLERANCE,
        },
        # UC3 generic
        _default_case()
        | {
            "_case_name": "uc2_assembly_with_bug",
            "folder": os.path.join("uc3_museum_guide", "Main"),
            "property_name": "tree_success",
        },
    ]


@pytest.mark.parametrize("case", get_cases(), ids=lambda c: c["_case_name"])
def test_scxml_to_jani(case):
    _test_with_main(**case)


@pytest.mark.xfail(reason="Expect removed functionalities not to work anymore.", strict=True)
def test_battery_example_w_bt_battery_depleted_removed():
    """Expect the property to be *not* satisfied."""
    c = _default_case() | {
        "_case_name": "ros_example_w_bt_removed_depleted",
        "folder": "ros_example_w_bt_removed",
        "property_name": "battery_depleted",
        "expected_result_probability": 0.0,
    }
    _test_with_main(*c)


@pytest.mark.xfail(reason="Expect removed functionalities not to work anymore.", strict=True)
def test_battery_example_w_bt_main_alarm_and_charge_removed():
    """Expect the property to be *not* satisfied."""
    c = _default_case() | {
        "_case_name": "ros_example_w_bt_removed_alarm_on",
        "folder": "ros_example_w_bt_removed",
        "property_name": "battery_alarm_on",
        "expected_result_probability": 0.0,
    }
    _test_with_main(*c)
