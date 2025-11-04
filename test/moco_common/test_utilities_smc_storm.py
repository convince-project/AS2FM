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
Helper functions to facilitate calling smc_storm and checking for
the desired output.
"""


import re
import subprocess
from typing import List, Tuple

import pytest


def _get_probability_from_output(output: str) -> float:
    """
    Interpret the output of the command's stdout and return a float.

    The expected pattern of a result is 'Result: 0.934'
    """
    results = re.findall(r"Result\: ([0-9]+\.?[0-9]*)", output)
    assert len(results) == 1, f"Expected to find exactly one result, {len(results)} found."
    result = float(results[0])
    assert result <= 1.0 and result >= 0.0, f"Result {result} not in [0, 1] set."
    return result


def _check_output_for_strings(
    output: str, expected_content: List[str], not_expected_content: List[str]
):
    """Interpret the output of the command. Make
    sure that the expected content is present and
    that the not expected content is not present."""
    for content in expected_content:
        assert content in output, f"Expected content {content} not found in output."
    for content in not_expected_content:
        assert content not in output, f"Unexpected content {content} found in output."


def _run_smc_storm(args: str) -> Tuple[str, str, int]:
    """Run smc_storm with the given arguments and return
    the stdout, stderr and return code."""
    command = f"smc_storm {args}"
    print("Running command: ", command)
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True
    ) as process:
        stdout, stderr = process.communicate()
        return_code = process.returncode
        print(f'stdout: """\n{stdout}"""')
        print(f'stderr: """\n{stderr}"""')
        print(f"return code: {return_code}")
        assert return_code == 0, f"Command failed with return code {return_code}"
    return stdout, stderr, return_code


def run_smc_storm_with_output(
    args: str,
    expected_content: List[str],
    not_expected_content: List[str],
    expected_result_probability: float,
    result_probability_tolerance: float,
):
    """Run smc_storm with the given arguments and check
    if the output is as expected."""
    stdout, stderr, result = _run_smc_storm(args)
    assert result == 0, "smc_storm failed to run"
    prob = _get_probability_from_output(stdout)
    error = abs(prob - expected_result_probability)
    assert error <= result_probability_tolerance, (
        f"Probability {prob} out of expected bounds: "
        f"{expected_result_probability} ± {result_probability_tolerance}"
    )
    _check_output_for_strings(stdout, expected_content, not_expected_content)
    _check_output_for_strings(stderr, [], not_expected_content)


def test_run_smc_storm():
    """Testing if it is possible to run smc_storm."""
    _, _, result = _run_smc_storm("-v")
    assert result == 0, "smc_storm failed to run"


def test_smc_storm_version():
    """Testing that you have the correct `smc_storm` version."""
    out, _, result = _run_smc_storm("-v")
    assert result == 0, "smc_storm failed to run"
    assert out.strip() == "0.1.8"


if __name__ == "__main__":
    pytest.main(["-s", "-vv", __file__])
