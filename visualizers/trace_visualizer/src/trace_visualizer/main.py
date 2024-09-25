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

from trace_visualizer.visualizer import Traces


def main_trace_to_png():
    parser = argparse.ArgumentParser(
        description='Converts a trace file produced by smc_storm into two' +
        ' images. One image for the first verified trace (if any) and one' +
        ' image for the first falsified trace (if any).')
    parser.add_argument('input_fname', type=str, help='The trace as csv file.')
    parser.add_argument(
        'output_png_prefix', type=str,
        help='Prefix for the output png file. ' +
        'The output will be saved as <prefix>_<verdict>.png')
    args = parser.parse_args()

    traces = Traces(args.input_fname)
    ver, fal = traces.print_info_about_result()
    if ver is not None:
        traces.write_trace_to_img(
            ver, args.output_png_prefix + "_verified.png")
    if fal is not None:
        traces.write_trace_to_img(
            fal, args.output_png_prefix + "_falsified.png")
