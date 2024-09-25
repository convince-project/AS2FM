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

import os
import random
from colorsys import hsv_to_rgb
from typing import Dict, List, Optional, Tuple

import pandas
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

LOC_PREFIX = '_loc_'
TRACE_NUMBER = 'Trace number'
RESULT = 'Result'
GLOBAL_TIMER = 'global_timer'
VERIFIED = 'Verified'

PIXELS_BORDER = 2
PIXELS_INTERNAL_BORDER = 1


def _hsv_to_rgb(h, s, v):
    """Converts an HSV color to an RGB color."""
    f_col = hsv_to_rgb(h, s, v)
    return tuple([int(x * 255) for x in f_col])


class Trace:
    """A single trace from a trace csv file produced by smc_storm."""

    def __init__(self, df):
        self._df = df

    def df(self) -> pandas.DataFrame:
        return self._df

    def is_verified(self) -> bool:
        return self._df[RESULT].dropna().item() == VERIFIED


class Traces:
    """A class to represent a trace csv file produced by smc_storm."""

    def __init__(self, fname):
        self.rng = random.Random(0)

        # Preparing data
        self.df = pandas.read_csv(fname, sep=';')
        self.columns = self.df.columns.values
        assert len(self.columns) > 1, 'Must have more than one column.'
        self.traces = self._separate_traces()
        self.automata = self._get_unique_automata()
        assert len(self.automata) > 1, 'Must have more than one automaton.'

        # Precomputations for visualization
        self.titles, self.titles_max_height, self.titles_max_width = \
            self._precompute_text()  # We swap width and height here because
        # the text was rotated by 90 degrees.
        self.color_per_automaton = self._get_color_per_automaton()
        assert len(self.color_per_automaton) == len(self.automata), \
            'Must have the same number of automata and colors.'
        self.data_per_automaton = self._get_data_per_automaton()
        assert len(self.data_per_automaton) == len(self.automata), \
            'Must have the same number of automata and data.'
        self.width_per_col = self._get_width_per_col()
        assert len(self.width_per_col) > 1, \
            'Must have more than one pixel no.'
        self.scale_per_col = self._get_scale_per_col()
        assert len(self.width_per_col) == len(self.scale_per_col), \
            'Must have the same number of widths and scale.'
        self.start_per_column = self._get_start_per_col()
        assert len(self.width_per_col) == len(self.start_per_column), \
            'Must have the same number of widths and starts.'
        self.img_width = self._get_img_width()
        print(f"{self.img_width=}")

    def print_info_about_result(self):
        """Plot index of first Verified and first Falsified trace."""
        verified: Optional[int] = None
        falsified: Optional[int] = None
        for i, trace in enumerate(self.traces):
            if trace.is_verified():
                if verified is None:
                    verified = i
            else:
                if falsified is None:
                    falsified = i
        print(
            'These are the first verified and falsified traces respectively:')
        print(f'{verified=}, {falsified=}')
        return verified, falsified

    def write_trace_to_img(self, trace_no: int, fname: str):
        """Write one trace to image file."""
        # Calculate the height of the image
        text_height = self.titles_max_height
        trace = self.traces[trace_no]
        print(trace.df())
        data_height = len(trace.df().index)
        print(f'{data_height=}')
        self.img_height = text_height + data_height \
            + 2 * PIXELS_BORDER + PIXELS_INTERNAL_BORDER
        image = Image.new(
            'RGB', (self.img_width, self.img_height), color='black')
        draw = ImageDraw.Draw(image)

        # Draw the automata names
        for a in self.automata:
            x = self.start_per_column[f'{LOC_PREFIX}{a}']
            y = PIXELS_BORDER
            bbox = self.titles[a].getbbox()
            # this_text_height = bbox[3] - bbox[1]
            # this_text_width = bbox[2] - bbox[0]
            # print(f'{a=}, {x=}, {y=}, {this_text_width=}, {this_text_height=}')
            colorized_text = ImageOps.colorize(
                self.titles[a], black='black',
                white=self.color_per_automaton[a][2])
            image.paste(colorized_text,
                        box=(x, y))
            # mask=self.titles[a])

        # Draw the data
        y_data_start = PIXELS_BORDER + text_height + PIXELS_INTERNAL_BORDER
        y_data_end = y_data_start + data_height
        for a in self.automata:
            for col in [f'{LOC_PREFIX}{a}'] + self.data_per_automaton[a]:
                x_start = self.start_per_column[col]
                width = self.width_per_col[col]
                scale = self.scale_per_col[col]
                if col.startswith(LOC_PREFIX):
                    bg_col = self.color_per_automaton[a][2]
                    fr_col = self.color_per_automaton[a][0]
                else:
                    bg_col = 'white'
                    fr_col = self.color_per_automaton[a][1]
                draw.rectangle(
                    [x_start, y_data_start, x_start + width - 1, y_data_end - 1],
                    fill=bg_col
                )
                y_0: Optional[int] = None
                for y_data, row in trace.df()[col].items():
                    if y_0 is None:
                        y_0 = y_data
                    y = y_data - y_0
                    if pandas.isna(row):
                        continue
                    if isinstance(row, str):
                        continue
                    try:
                        x = int(row * scale)
                    except TypeError as e:
                        print(e)
                        print(f'{row=}')
                    assert x >= 0, f'{x=} must be positive.'
                    assert x < width, \
                        f'{x=} must be smaller than {width=}. ({scale=},' + \
                        f' {type(row)=}, {row=})'
                    draw.point(
                        (x_start + x, y_data_start + y),
                        fill=fr_col
                    )

        # Plot result
        # find line where Result is not none
        result: bool = trace.is_verified()
        color = 'green' if result else 'red'
        draw.rectangle(
            [PIXELS_BORDER,
             self.img_height - PIXELS_BORDER - 1,
             self.img_width - PIXELS_BORDER - 1,
             self.img_height - PIXELS_BORDER - 1],
            fill=color
        )

        # Write the image to file
        image.save(fname)

    def _precompute_text(self):
        """Create the header of the image."""
        texts = {}
        max_height = 0
        max_width = 0
        enhancer = ImageEnhance.Contrast
        font_path = os.path.join(
            os.path.dirname(__file__), 'data', 'slkscr.ttf')
        for automaton in self.automata:
            f = ImageFont.truetype(font_path, 7)
            bbox = f.getbbox(automaton)
            width = bbox[2] - bbox[0]
            max_width = max(max_width, width)
            height = 7  # bbox[3] - bbox[1]
            max_height = max(max_height, height)
            # print(f'{automaton=}, {bbox=}, {width=}, {height=}')
            txt = Image.new('L', (width, height), color=0)
            d = ImageDraw.Draw(txt)
            d.text((0, 0), automaton, font=f, fill=255)
            txt = enhancer(txt).enhance(10.0)
            hist = txt.histogram()
            # for i in range(256):
            #     if hist[i] == 0:
            #         continue
            #     assert i == 255 or i == 0, \
            #         f'This should be pure black or white. {i=} {hist[i]=}'
            bbox = txt.getbbox()
            txt = txt.crop(bbox)
            txt_rot = txt.rotate(90, expand=1)
            texts[automaton] = txt_rot
        return texts, max_width, max_height

    def _separate_traces(self) -> List[Trace]:
        """Separates the traces in the dataframe into Trace objects."""
        assert TRACE_NUMBER in self.columns, \
            f'Must have a column named "{TRACE_NUMBER}"'
        unique_traces = self.df[TRACE_NUMBER].unique()
        unique_traces.sort()
        traces = []
        for trace in unique_traces:
            traces.append(Trace(self.df[self.df[TRACE_NUMBER] == trace]))
        print(f'{len(traces)=}')
        return traces

    def _get_unique_automata(self) -> List[str]:
        """Returns a list of names of automata in the traces."""
        all_automata = sorted([
            x.replace(LOC_PREFIX, '')
            for x in self.columns
            if x.startswith(LOC_PREFIX)
        ])
        if GLOBAL_TIMER in all_automata:
            all_automata.remove(GLOBAL_TIMER)
            return [GLOBAL_TIMER] + all_automata
        return all_automata

    def _get_color_per_automaton(self) -> Dict[
            str, Tuple[
                Tuple[int, int, int],
                Tuple[int, int, int],
                Tuple[int, int, int]]
    ]:
        """Returns a dictionary with the color of each automaton."""
        colors = {}
        random_automata_i = list(range(len(self.automata)))
        self.rng.shuffle(random_automata_i)
        for i, automaton in enumerate(self.automata):
            i_color = random_automata_i[i]
            hue = i_color / len(self.automata)
            if automaton == GLOBAL_TIMER:
                # gray
                colors[automaton] = (
                    _hsv_to_rgb(hue, 0, .5),  # dark
                    _hsv_to_rgb(hue, 0, .7),  # mid
                    _hsv_to_rgb(hue, 0, 1)    # light
                )
            else:
                colors[automaton] = (
                    _hsv_to_rgb(hue, 1, .5),  # dark
                    _hsv_to_rgb(hue, 1, .7),  # mid
                    _hsv_to_rgb(hue, .2, 1)   # light
                )
        return colors

    def _get_data_per_automaton(self) -> Dict[str, List[str]]:
        """Returns a dictionary with the data column names that can be
        somhow related to that automaton. This is only done by comparing
        the name, so it is not perfect."""
        data_per_automaton: Dict[str, List[str]] = {
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
            width_per_col[f'{LOC_PREFIX}{a}'] = int(self.df[f'{LOC_PREFIX}{a}'].max() + 1)
            # print(width_per_col[f'{LOC_PREFIX}{a}'])
            # print(self.data_per_automaton[a])
            for col in self.data_per_automaton[a]:
                # print(self.df[col].dtype)
                if self.df[col].dtype == 'float64':
                    width_per_col[col] = int(min(self.df[col].max() + 1, 10))
                else:  # we assume this is a binary
                    width_per_col[col] = 2
        return width_per_col

    def _get_scale_per_col(self) -> Dict[str, float]:
        """Calculate the scale for each column."""
        scale_per_col = {}
        for col in self.width_per_col:
            scale_per_col[col] = 1.0
            try:
                if self.df[col].max()+1 > 10:
                    scale_per_col[col] = 10.0 / (self.df[col].max()+1)
            except TypeError as e:
                print(e)
        return scale_per_col

    def _get_start_per_col(self):
        """Calculate where each of the column areas should start,
        taking widths and boders into account. (Width only)"""
        start_per_col = {}
        current_loc = PIXELS_BORDER
        start_last_automaton: Optional[int] = None
        for a in self.automata:
            if start_last_automaton is not None:
                current_loc = max(
                    current_loc, start_last_automaton + self.titles_max_width
                    + PIXELS_INTERNAL_BORDER)
            start_automaton = current_loc
            for col in [f'{LOC_PREFIX}{a}'] + self.data_per_automaton[a]:
                start_per_col[col] = current_loc
                this_width = self.width_per_col[col]
                current_loc += (this_width + PIXELS_INTERNAL_BORDER)
            start_last_automaton = start_automaton
        return start_per_col

    def _get_img_width(self) -> int:
        """Calculate the width of the image."""
        last_col = self.data_per_automaton[self.automata[-1]][-1]
        return (
            self.start_per_column[last_col] + self.width_per_col[last_col]
            + PIXELS_BORDER
        )
