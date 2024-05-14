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

"""
Module containing the main entry point, pulling all necessary files together.
convince.jani \
BT.xml         \
plugin.scxml    \
node1.scxml      => main.py  =>  output.jani
node2.scxml     /
env.scxml      /
"""

import argparse
import os
import sys
import timeit
import json
from typing import Optional, Sequence

from jani_generator.jani_entries import JaniModel
from jani_generator.convince_jani_helpers import convince_jani_parser


def main(args: Optional[Sequence[str]] = None) -> int:
    """
    Entry point for the application.
    """
    parser = argparse.ArgumentParser(description='Convert many files to Jani.')
    parser.add_argument('--convince_jani', help='The convince-jani file.', type=str, required=True)
    # parser.add_argument('--bt_xml', help='The BT XML file.', type=str, required=False)
    # parser.add_argument('--plugins_scxml', help='The plugin SCXML files.', type=str, nargs='+', required=False)
    # parser.add_argument('--nodes_scxml', help='The node SCXML files.', type=str, nargs='+', required=False)
    # parser.add_argument('--env_scxml', help='The environment SCXML file.', type=str, required=False)
    parser.add_argument('--output', help='The output Plain Jani file.', type=str, required=True)
    args = parser.parse_args(args)

    start_time = timeit.default_timer()
    model_loaded = False
    jani_model = JaniModel()
    if args.convince_jani is not None:
        assert os.path.isfile(args.convince_jani), f"File {args.convince_jani} does not exist."
        # Check the file's extension
        _, extension = os.path.splitext(args.convince_jani)
        assert extension == ".jani", f"File {args.convince_jani} is not a Jani file."
        convince_jani_parser(jani_model, args.convince_jani)
        model_loaded = True
    # if args.env_scxml is not None:
    #     pass
    # if args.bt_xml is not None:
    #     pass
    # if args.plugins_scxml is not None:
    #     pass
    # if args.nodes_scxml is not None:
    #     pass
    assert model_loaded, "No input file was provided. Check your input."
    # for f in [args.bt_xml, args.env_scxml] + args.plugins_scxml + args.nodes_scxml:
    #     if not os.path.exists(f):
    #         print(f"File {f} does not exist.")
    #         return os.EX_NOINPUT
    # Write the loaded model to the output file
    with open(args.output, "w") as output_file:
        json.dump(jani_model.as_dict(), output_file, indent=4, ensure_ascii=False)
    print(f"Converted jani model written to {args.output}.")
    print(f"Conversion took {timeit.default_timer() - start_time} seconds.")


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
