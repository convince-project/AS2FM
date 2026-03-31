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
import os
from typing import Optional, Sequence

from as2fm.as2fm_common.logging import get_warn_msg
from as2fm.jani_generator.scxml_helpers.top_level_interpreter import interpret_top_level_xml


def roaml_to_jani(_args: Optional[Sequence[str]] = None) -> None:
    """
    Main function for the RoAML model (with ASCXML models) to JANI conversion.

    The RoAML model describes the full system, and pulls all necessary files together:
    properties.jani \
    BT.xml           \
    plugin.ascxml     \
    node1.ascxml       => roaml_to_jani  =>  main.jani
    node2.ascxml      /
    env.ascxml       /

    :param args: The arguments to parse. If None, sys.argv is used.
    :return: None
    """
    parser = argparse.ArgumentParser(description="Convert SCXML robot system models to JANI model.")
    parser.add_argument(
        "--scxml-out-dir",
        type=str,
        default="",
        help="Path to the folder containing the generated plain-SCXML files.",
    )
    parser.add_argument(
        "--jani-out-file", type=str, default="", help="Path to the generated jani file."
    )
    parser.add_argument("roaml_xml", type=str, help="The path to the RoAML XML file to interpret.")
    args = parser.parse_args(_args)

    # Check the main xml file provided by the user
    main_xml_file = args.roaml_xml
    assert os.path.isfile(main_xml_file), f"File {main_xml_file} does not exist."
    assert main_xml_file.endswith(".xml"), "File {main_xml_file} is not a '.xml' file."
    # Process additional, optional parameters
    scxml_out_dir = args.scxml_out_dir
    scxml_out_dir = None if len(scxml_out_dir) == 0 else scxml_out_dir
    jani_out_file = args.jani_out_file
    jani_out_file = None if len(jani_out_file) == 0 else jani_out_file

    # Proceed with the conversion
    print("AS2FM - RoAML to JANI.\n")
    print(f"Loading model from {main_xml_file}.")
    interpret_top_level_xml(main_xml_file, jani_file=jani_out_file, scxmls_dir=scxml_out_dir)


def main_scxml_to_jani(_args: Optional[Sequence[str]] = None) -> None:
    """Support function for the old enry-point. Deprecated!"""
    get_warn_msg(
        None,
        "The `main_scxml_to_jani` executable is deprecated. "
        "Switch to the new `roaml_to_jani` one.",
    )
    roaml_to_jani(_args)


if __name__ == "__main__":
    # for testing purposes only
    import sys

    roaml_to_jani(sys.argv[1:])
