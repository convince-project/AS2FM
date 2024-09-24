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

import pandas
from PIL import Image, ImageDraw
from typing import Dict, List
from colorsys import hsv_to_rgb


LOC_PREFIX = '_loc_'
TRACE_NUMBER = 'Trace number'
RESULT = 'Result'

PIXELS_BORDER = 2
PIXELS_BETWEEN_COLUMNS = 1


class Trace:
    """A single trace from a trace csv file produced by smc_storm."""

    def __init__(self, df):
        self.df = df
        self.img = None

    def df(self) -> pandas.DataFrame:
        return self.df


class Traces:
    """A class to represent a trace csv file produced by smc_storm."""

    def __init__(self, fname):
        # Preparing data
        self.df = pandas.read_csv(fname, sep=';')
        self.columns = self.df.columns.values
        assert len(self.columns) > 1, 'Must have more than one column.'
        self.traces = self._separate_traces()
        self.automata = self._get_unique_automata()
        assert len(self.automata) > 1, 'Must have more than one automaton.'

        # Precomputations for visualization
        self.color_per_automaton = self._get_color_per_automaton()
        assert len(self.color_per_automaton) == len(self.automata), \
            'Must have the same number of automata and colors.'
        self.data_per_automaton = self._get_data_per_automaton()
        assert len(self.data_per_automaton) == len(self.automata), \
            'Must have the same number of automata and data.'
        self.width_per_col = self._get_width_per_col()
        assert len(self.width_per_col) > 1, 'Must have more than one pixel no.'
        self.width = self._get_img_width()
        print(self.width)
        self.start_per_column = self._get_start_per_col()
        assert len(self.width_per_col) == len(self.start_per_column), \
            'Must have the same number of widths and starts.'
        
    def write_trace_to_img(self, trace_no: int, fname: str):
        """Write one trace to image file."""
        trace = self.traces[trace_no]
        height = len(trace.df.index)
        image = Image.new('RGB', (self.width, height), color='black')
        draw = ImageDraw.Draw(image)
        for a in self.automata:
            for col in [f'{LOC_PREFIX}{a}'] + self.data_per_automaton[a]:
                start = self.start_per_column[col]
                width = self.width_per_col[col]
                draw.rectangle(
                    [start, 0, start + width - 1, height],
                    fill='white'
                )
                for i, row in trace.df[col].iteritems():
                    draw.point(
                        (start + row, i),
                        fill='grey'
                    )        
        image.save(fname)

    def _separate_traces(self) -> List[Trace]:
        """Separates the traces in the dataframe into individual Trace objects."""
        assert TRACE_NUMBER in self.columns, f'Must have a column named "{TRACE_NUMBER}"'
        unique_traces = self.df[TRACE_NUMBER].unique()
        unique_traces.sort()
        traces = []
        for trace in unique_traces:
            traces.append(Trace(self.df[self.df[TRACE_NUMBER] == trace]))
        return traces

    def _get_unique_automata(self) -> List[str]:
        """Returns a list of names of automata in the traces."""
        return sorted([
            x.replace(LOC_PREFIX, '') 
            for x in self.columns 
            if x.startswith(LOC_PREFIX)
        ])
    
    def _get_color_per_automaton(self) -> Dict[str, str]:
        """Returns a dictionary with the color of each automaton."""
        colors = {}
        for i in range(len(self.automata)):
            (r, g, b) = hsv_to_rgb(i / len(self.automata), 1, 1)
            colors[self.automata[i]] = (
                int(r * 255),
                int(g * 255),
                int(b * 255)
            )
        return colors
    
    def _get_data_per_automaton(self) -> Dict[str, List[str]]:
        """Returns a dictionary with the data column names that can be
        somhow related to that automaton. This is only done by comparing
        the name, so it is not perfect."""
        data_per_automaton = {
            automaton: []
            for automaton in self.automata
        }
        for col in self.columns:
            if col.startswith(LOC_PREFIX):
                continue
            if col.startswith('Unnamed: '):
                continue
            if col == TRACE_NUMBER:
                continue
            if col == RESULT:
                continue
            # going to automata names in reverse order,
            # so that the longest automata name is matched first
            found = False
            for automaton in reversed(self.automata):
                if automaton in col:
                    data_per_automaton[automaton].append(col)
                    found = True
                    break
            if not found:
                print(f'Could not match column "{col}" to any automaton')
        return data_per_automaton
    
    def _get_width_per_col(self) -> Dict[str, int]:
        """
        Determine how many pixels are needed to represent the different columns.
        
        - 1 pixel per state in the automaton location
        - 1 pixel for binary data
        - max(data) pixels for integer data but not more than 10 pixels
        """
        width_per_col = {}
        for a in self.automata:
            width_per_col[f'{LOC_PREFIX}{a}'] = int(self.df[f'{LOC_PREFIX}{a}'].max())
            # print(width_per_col[f'{LOC_PREFIX}{a}'])
            # print(self.data_per_automaton[a])
            for col in self.data_per_automaton[a]:
                # print(self.df[col].dtype)
                if self.df[col].dtype == 'float64':
                    width_per_col[col] = min(self.df[col].max(), 10)
                else:  # we assume this is a binary
                    width_per_col[col] = 1
        return width_per_col
    
    def _get_img_width(self) -> int:
        """Calculate the width of the image."""
        return (
            (len(self.width_per_col) - 1) * PIXELS_BETWEEN_COLUMNS +  # spaces between columns
            sum(self.width_per_col.values()) +  # pixels for data
            2 * PIXELS_BORDER  # border (left and right)
        )
    
    def _get_start_per_col(self):
        """Calculate where each of the column areas should start,
        taking widths and boders into account. (Width only)"""
        start_per_col = {}
        current_loc = PIXELS_BORDER
        for a in self.automata:
            for col in [f'{LOC_PREFIX}{a}'] + self.data_per_automaton[a]:
                start_per_col[col] = current_loc
                this_width = self.width_per_col[col]
                current_loc += (this_width + PIXELS_BETWEEN_COLUMNS)
        return start_per_col