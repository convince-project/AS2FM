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

import subprocess

import pytest


def _run_smc_storm(args: str):
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
    print("smc_storm stdout:")
    print(stdout)
    print("smc_storm stderr:")
    print(stderr)
    print("smc_storm return code:")
    print(return_code)
    assert return_code == 0, \
        f"Command failed with return code {return_code}"
    return return_code == 0


def test_run_smc_storm():
    """Testing if it is possible to run smc_storm."""
    result = _run_smc_storm("-v")
    assert result, "smc_storm failed to run"


if __name__ == '__main__':
    pytest.main(['-s', '-vv', __file__])
