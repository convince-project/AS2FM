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

import argparse
import json
import os
import timeit
from typing import Optional, Sequence

from as2fm.jani_generator.convince_jani_helpers import convince_jani_parser
from as2fm.jani_generator.jani_entries import JaniModel
from as2fm.jani_generator.scxml_helpers.top_level_interpreter import interpret_top_level_xml


def main_scxml_to_jani(_args: Optional[Sequence[str]] = None) -> None:
    """
    Main function for the SCXML to JANI conversion.

    Module containing the main entry points, pulling all necessary files together.
    convince.jani \
    BT.xml         \
    plugin.scxml    \
    node1.scxml      => main_scxml_to_jani  =>  main.jani
    node2.scxml     /
    env.scxml      /

    :param args: The arguments to parse. If None, sys.argv is used.
    :return: None
    """
    parser = argparse.ArgumentParser(description="Convert SCXML robot system models to JANI model.")
    parser.add_argument(
        "--generated-scxml-dir",
        type=str,
        default="",
        help="Path to the folder containing the generated plain-SCXML files.",
    )
    parser.add_argument(
        "--jani-out-file", type=str, default="", help="Path to the generated jani file."
    )
    parser.add_argument("main_xml", type=str, help="The path to the main XML file to interpret.")
    args = parser.parse_args(_args)

    # Check the main xml file provided by the user
    main_xml_file = args.main_xml
    assert os.path.isfile(main_xml_file), f"File {main_xml_file} does not exist."
    assert main_xml_file.endswith(".xml"), "File {main_xml_file} is not a '.xml' file."
    # Process additional, optional parameters
    scxml_out_dir = args.generated_scxml_dir
    scxml_out_dir = None if len(scxml_out_dir) == 0 else scxml_out_dir
    jani_out_file = (
        args.jani_out_file
        if len(args.jani_out_file) > 0
        else main_xml_file.removesuffix("xml") + "jani"
    )

    print("AS2FM - SCXML to JANI.\n")
    print(f"Loading model from {main_xml_file}.")

    interpret_top_level_xml(main_xml_file, jani_file=jani_out_file, scxmls_dir=scxml_out_dir)


def main_convince_to_plain_jani(_args: Optional[Sequence[str]] = None) -> None:
    """
    Entry point for the conversion of a CONVINCE JANI file to a plain JANI file.

    :param args: The arguments to parse. If None, sys.argv is used.
    :return: None
    """
    parser = argparse.ArgumentParser(description="Convert CONVINCE JANI to plain JANI.")
    parser.add_argument("--convince_jani", help="The convince-jani file.", type=str, required=True)
    parser.add_argument("--output", help="The output Plain JANI file.", type=str, required=True)
    args = parser.parse_args(_args)

    start_time = timeit.default_timer()
    model_loaded = False
    jani_model = JaniModel()
    if args.convince_jani is not None:
        assert os.path.isfile(args.convince_jani), f"File {args.convince_jani} does not exist."
        # Check the file's extension
        _, extension = os.path.splitext(args.convince_jani)
        assert extension == ".jani", f"File {args.convince_jani} is not a JANI file."
        convince_jani_parser(jani_model, args.convince_jani)
        model_loaded = True
    assert model_loaded, "No input file was provided. Check your input."
    # Write the loaded model to the output file
    with open(args.output, "w", encoding="utf-8") as output_file:
        json.dump(jani_model.as_dict(), output_file, indent=4, ensure_ascii=False)
    print(f"Converted jani model written to {args.output}.")
    print(f"Conversion took {timeit.default_timer() - start_time} seconds.")


def main_bt_only_verification(_args: Optional[Sequence[str]] = None) -> None:
    """
    Main function for BT-only verification using mock plugins.

    This mode generates mock plugins for all BT conditions and actions,
    enabling thorough verification of BT logic without external system constraints.

    :param args: The arguments to parse. If None, sys.argv is used.
    :return: None
    """
    parser = argparse.ArgumentParser(
        description="Convert Behavior Tree to JANI model using mock plugins for thorough"
        "verification."
    )
    parser.add_argument(
        "--bt-xml", type=str, required=True, help="Path to the Behavior Tree XML file."
    )
    parser.add_argument(
        "--properties", type=str, required=True, help="Path to the JANI properties file."
    )
    parser.add_argument(
        "--max-time",
        type=int,
        default=100,
        help="Maximum simulation time in seconds (default: 100).",
    )
    parser.add_argument(
        "--bt-tick-rate", type=float, default=1.0, help="BT tick rate in Hz (default: 1.0)."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible mock behavior (default: None).",
    )
    parser.add_argument(
        "--jani-out-file",
        type=str,
        default="",
        help="Path to the generated JANI file (default: bt_verification.jani).",
    )
    parser.add_argument(
        "--generated-scxml-dir",
        type=str,
        default="",
        help="Path to the folder containing the generated plain-SCXML files.",
    )
    parser.add_argument(
        "--condition-success-probability",
        type=float,
        default=0.5,
        help="Success probability for condition nodes (default: 0.5).",
    )
    parser.add_argument(
        "--action-success-probability",
        type=float,
        default=0.6,
        help="Success probability for action nodes (default: 0.6).",
    )
    parser.add_argument(
        "--action-running-probability",
        type=float,
        default=0.2,
        help="Running probability for action nodes (default: 0.2).",
    )
    args = parser.parse_args(_args)

    # Validate input files
    assert os.path.isfile(args.bt_xml), f"BT XML file {args.bt_xml} does not exist."
    assert os.path.isfile(args.properties), f"Properties file {args.properties} does not exist."

    # Set output file name
    jani_out_file = args.jani_out_file if args.jani_out_file else "bt_verification.jani"

    print("AS2FM - BT-Only Verification with Mock Plugins.\n")
    print(f"Loading BT from {args.bt_xml}.")
    print(f"Using properties from {args.properties}.")
    print(f"Random seed: {args.seed}")

    start_time = timeit.default_timer()

    # Import here to avoid circular imports
    from as2fm.jani_generator.jani_entries import JaniProperty
    from as2fm.jani_generator.ros_helpers.ros_timer import RosTimer
    from as2fm.jani_generator.scxml_helpers.scxml_to_jani import (
        convert_multiple_scxmls_to_jani,
        preprocess_jani_expressions,
    )
    from as2fm.scxml_converter.mock_bt_generator import create_mock_bt_converter_scxml

    # Generate mock BT SCXML models using SCXML templates
    print("Using SCXML template-based mock generation.")
    mock_scxml_models = create_mock_bt_converter_scxml(
        bt_xml_path=args.bt_xml,
        bt_tick_rate=args.bt_tick_rate,
        tick_if_not_running=True,  # Always tick when not running for thorough verification
        custom_data_types={},  # No custom data types needed for mock plugins
        seed=args.seed,
        condition_success_probability=args.condition_success_probability,
        action_success_probability=args.action_success_probability,
        action_running_probability=args.action_running_probability,
    )

    # Convert to plain SCXML and collect timers
    plain_scxml_models = []
    all_timers = []
    for scxml_model in mock_scxml_models:
        plain_scxmls, ros_declarations = scxml_model.to_plain_scxml_and_declarations()
        for plain_scxml in plain_scxmls:
            plain_scxml.set_xml_origin(scxml_model.get_xml_origin())
        # Handle ROS timers
        for timer_name, timer_rate in ros_declarations._timers.items():
            all_timers.append(RosTimer(timer_name, timer_rate))
        plain_scxml_models.extend(plain_scxmls)

    # Add global timer SCXML if there are timers
    if all_timers:
        from as2fm.jani_generator.ros_helpers.ros_timer import make_global_timer_scxml

        max_time_ns = args.max_time * 1_000_000_000  # Convert seconds to nanoseconds
        timer_scxml = make_global_timer_scxml(all_timers, max_time_ns)
        if timer_scxml is not None:
            timer_scxml.set_custom_data_types({})
            timer_plain_scxmls, _ = timer_scxml.to_plain_scxml_and_declarations()
            plain_scxml_models.extend(timer_plain_scxmls)

    # Convert to JANI
    jani_model = convert_multiple_scxmls_to_jani(plain_scxml_models, 100)  # Default max array size

    # Add properties
    with open(args.properties, "r", encoding="utf-8") as f:
        all_properties = json.load(f)["properties"]
        for property_dict in all_properties:
            jani_model.add_jani_property(JaniProperty.from_dict(property_dict))

    # Preprocess the JANI file
    preprocess_jani_expressions(jani_model)

    # Write output
    with open(jani_out_file, "w", encoding="utf-8") as f:
        json.dump(jani_model.as_dict(), f, indent=2, ensure_ascii=False)

    print(f"BT verification model written to {jani_out_file}.")
    print(f"Conversion took {timeit.default_timer() - start_time} seconds.")


if __name__ == "__main__":
    # for testing purposes only
    import sys

    main_scxml_to_jani(sys.argv[1:])
