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
from typing import Annotated

import typer

from as2fm.jani_generator.convince_jani_helpers import convince_jani_parser
from as2fm.jani_generator.jani_entries import JaniModel
from as2fm.jani_generator.scxml_helpers.top_level_interpreter import interpret_top_level_xml

as2fm_convince_to_plain_jani = typer.Typer()


@as2fm_convince_to_plain_jani.command()
def main_convince_to_plain_jani(
    convince_jani: Annotated[typer.FileText, typer.Option()],
    output: Annotated[typer.FileTextWrite, typer.Option()],
) -> None:
    """
    Entry point for the conversion of a CONVINCE JANI file to a plain JANI file.

    :param args: The arguments to parse. If None, sys.argv is used.
    :return: None
    """

    start_time = timeit.default_timer()
    model_loaded = False
    jani_model = JaniModel()
    if convince_jani is not None:
        # Check the file's extension
        _, extension = os.path.splitext(convince_jani.name)
        assert extension == ".jani", f"File {convince_jani.name} is not a JANI file."
        convince_jani_parser(jani_model, convince_jani)
        model_loaded = True
    assert model_loaded, "No input file was provided. Check your input."
    # Write the loaded model to the output file
    json.dump(jani_model.as_dict(), output, indent=4, ensure_ascii=False)
    print(f"Converted jani model written to {output}.")
    print(f"Conversion took {timeit.default_timer() - start_time} seconds.")


as2fm_scxml_to_jani = typer.Typer()


@as2fm_scxml_to_jani.command("as2fm_scxml_to_jani")
def main_scxml_to_jani(o: str) -> None:
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
    args = parser.parse_args()

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

    interpret_top_level_xml(main_xml_file, jani_out_file, scxml_out_dir)


if __name__ == "__main__":
    # for testing purposes only
    import sys

    main_scxml_to_jani(sys.argv[1:])
