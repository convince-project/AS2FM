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
        "--jani-out-file", type=str, default="main.jani", help="Path to the generated jani file."
    )
    parser.add_argument("main_xml", type=str, help="The path to the main XML file to interpret.")
    args = parser.parse_args(_args)

    main_xml_file = args.main_xml
    scxml_out_dir = args.generated_scxml_dir
    scxml_out_dir = None if len(scxml_out_dir) == 0 else scxml_out_dir
    jani_out_file = args.jani_out_file
    # Very basic input args checks
    assert os.path.isfile(main_xml_file), f"File {main_xml_file} does not exist."
    assert len(jani_out_file) > 0, "Output file not provided."

    interpret_top_level_xml(main_xml_file, jani_out_file, scxml_out_dir)
