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

import plantuml

from as2fm.jani_visualizer.visualizer import PlantUMLAutomata


def main_jani_to_plantuml():
    parser = argparse.ArgumentParser(description="Converts a `*.jani` file to a `*.plantuml` file.")
    parser.add_argument("input_fname", type=str, help="The input jani file.")
    parser.add_argument("output_plantuml_fname", type=str, help="The output plantuml file.")
    parser.add_argument("output_svg_fname", type=str, help="The output svg file.")
    parser.add_argument(
        "--no-syncs",
        action="store_true",
        help="Don't connects transitions that are synchronized.",
    )
    parser.add_argument(
        "--no-assignments",
        action="store_true",
        help="Don't show assignments on the edges.",
    )
    parser.add_argument("--no-guard", action="store_true", help="Don't show guards on the edges.")
    args = parser.parse_args()

    assert os.path.isfile(args.input_fname), f"File {args.input_fname} must exist."
    try:
        with open(args.input_fname, "r") as f:
            jani_dict = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error while reading the input file {args.input_fname}") from e

    assert not os.path.isfile(
        args.output_plantuml_fname
    ), f"File {args.output_plantuml_fname} must not exist."

    assert not os.path.isfile(
        args.output_svg_fname
    ), f"File {args.output_svg_fname} must not exist."

    pua = PlantUMLAutomata(jani_dict)
    puml_str = pua.to_plantuml(
        with_assignments=not args.no_assignments,
        with_guards=not args.no_guard,
        with_syncs=not args.no_syncs,
    )
    with open(args.output_plantuml_fname, "w") as f:
        f.write(puml_str)

    plantuml.PlantUML("http://www.plantuml.com/plantuml/img/").processes_file(
        args.output_plantuml_fname, outfile=args.output_svg_fname
    )
    url = plantuml.PlantUML("http://www.plantuml.com/plantuml/img/").get_url(puml_str)
    print(f"{url=}")
