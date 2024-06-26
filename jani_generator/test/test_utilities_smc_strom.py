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

from typing import List, Tuple

import subprocess

import pytest


def _interpret_output(
        output: str,
        expected_content: List[str],
        not_expected_content: List[str]):
    """Interpret the output of the command. Make
    sure that the expected content is present and
    that the not expected content is not present."""
    for content in expected_content:
        assert content in output, f"Expected content {content} not found in output."
    for content in not_expected_content:
        assert content not in output, f"Unexpected content {content} found in output."


def _run_smc_storm(args: str) -> Tuple[str, str, int]:
    command = f"smc_storm {args}"
    print("Running command: ", command)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        universal_newlines=True
    )
    stdout, stderr = process.communicate()
    return_code = process.returncode
    print(f"stdout: \"\"\"\n{stdout}\"\"\"")
    print(f"stderr: \"\"\"\n{stderr}\"\"\"")
    print(f"return code: {return_code}")
    assert return_code == 0, \
        f"Command failed with return code {return_code}"
    return stdout, stderr, return_code


def run_smc_storm_with_output(
        args: str,
        expected_content: List[str],
        not_expected_content: List[str]):
    """Run smc_storm with the given arguments and check
    if the output is as expected."""
    stdout, stderr, result = _run_smc_storm(args)
    assert result == 0, "smc_storm failed to run"
    _interpret_output(stdout, expected_content, not_expected_content)
    _interpret_output(stderr, [], not_expected_content)


def test_run_smc_storm():
    """Testing if it is possible to run smc_storm."""
    _, _, result = _run_smc_storm("-v")
    assert result == 0, "smc_storm failed to run"


if __name__ == '__main__':
    pytest.main(['-s', '-vv', __file__])
