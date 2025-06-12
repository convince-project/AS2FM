import os
import subprocess
from collections import OrderedDict
from pathlib import Path

import pytest
from sybil import Sybil
from sybil.parsers.codeblock import CodeBlockParser
from sybil.parsers.rest.lexers import DirectiveInCommentLexer

COMMAND_PREFIX = "$ "
IGNORED_OUTPUT = "..."
DIR_NEW_ENV = "sybil-new-environment"
DIR_CODE_BLOCK = "code-block"
BASH = "bash"
OPTIONS = "options"
IGNORE = "IGNORE"
LINE_END = "\\"
CWD = "cwd"
EXPECTED_FILES = "expected-files"

AS2FM_FOLDER = os.path.join(__file__, "..", "..")


def evaluate_bash_block(example, cwd):
    """Executes a command and compares it's output to the provided expected output.

    ```
    .. code-block:: bash

        $ command

        expected output
        ...
    ```
    """
    lines = example.parsed.strip().split("\n")
    output = []
    output_i = -1
    previous_cmd_line = ""
    for line in lines:
        if line.startswith(COMMAND_PREFIX):
            # this is a command
            command = previous_cmd_line + line.replace(COMMAND_PREFIX, "")
            if command.endswith(LINE_END):
                # this must be merged with the next line
                previous_cmd_line = command.replace(LINE_END, "")
                continue
            print(f"{command=}")
            previous_cmd_line = ""
            output = (
                subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True, cwd=cwd)
                .strip()
                .decode("ascii")
            )
            print(f"{output=}")
            output = [x.strip() for x in output.split("\n")]
            output_i = 0
        else:
            # this is expected output
            expected_line = line.strip()
            if len(expected_line) == 0:
                continue
            if output_i >= len(output):
                # end of captured output
                output_i = -1
                continue
            if output_i == -1:
                continue
            actual_line = output[output_i]
            while len(actual_line) == 0:
                # skip empty lines
                output_i += 1
                if output_i >= len(output):
                    output_i = -1
                    continue
                actual_line = output[output_i]
            if IGNORED_OUTPUT in expected_line:
                # skip this line
                output_i += 1
                continue
            assert actual_line == expected_line
            output_i += 1


def collect_docs():
    """Search for *.rst files under `docs/source`."""
    docs_folder_path = Path(__file__).parent / "source"
    assert docs_folder_path.exists(), f"Docs path doesn't exist: {docs_folder_path.resolve()}"

    all_rst_files = list(docs_folder_path.glob("*.rst"))
    print(f"Found {len(all_rst_files)} .rst files in docs folder.")

    # Configure Sybil
    bash_parser = CodeBlockParser(language=BASH)
    directive_parser = DirectiveInCommentLexer(directive=DIR_NEW_ENV)
    sybil = Sybil(
        parsers=[bash_parser, directive_parser],
        pattern="*.rst",
        path=docs_folder_path.as_posix(),
    )
    documents = []
    for f_path in all_rst_files:
        doc = sybil.parse(f_path)
        rel_path = os.path.relpath(f_path, AS2FM_FOLDER)
        if len(list(doc)) > 0:
            documents.append([rel_path, list(doc)])
    print(f"Found {len(documents)} .rst files with code to test.")
    return documents


@pytest.mark.parametrize("path, blocks", collect_docs())
def test_doc_rst(path, blocks):
    """Testing all code blocks in one *.rst file under `path`."""
    print(f"Testing {len(blocks)} code blocks in {path}.")
    env_blocks = OrderedDict()
    env_options = OrderedDict()
    current_env = "DEFAULT"
    for block in blocks:
        directive = block.region.lexemes["directive"]
        arguments = block.region.lexemes["arguments"]
        if directive == DIR_NEW_ENV:
            # This is a `sybil-new-environment` block with some options.
            assert arguments not in env_blocks.keys()
            current_env = arguments
            if arguments == IGNORE:
                continue
            if OPTIONS in block.region.lexemes:
                env_options[arguments] = block.region.lexemes[OPTIONS]
        elif directive == DIR_CODE_BLOCK:
            # This is a bash code block.
            if current_env == IGNORE:
                continue
            assert arguments == BASH
            if current_env not in env_blocks.keys():
                env_blocks[current_env] = []
            env_blocks[current_env].append(block)
    # After preprocessing all the environments, evaluate them.
    for env, blocks in env_blocks.items():
        if env in env_options:
            options = env_options[env]
        else:
            options = {}
        print(f"Evaluating environment >{env}< with {options} ...")
        if CWD not in options:
            options[CWD] = "."
        cwd = os.path.realpath(os.path.join(AS2FM_FOLDER, options[CWD]))
        print(f"In folder {cwd}")
        expected_files = []

        # Check preconditions
        if EXPECTED_FILES in options:
            for file in options[EXPECTED_FILES].split(","):
                expected_files.append(os.path.join(cwd, file.strip()))
                assert not os.path.isfile(
                    expected_files[-1]
                ), f"File {expected_files[-1]} was *not* expected to exist before the test."
        # Execute all blocks in this environment
        try:
            for block in blocks:
                evaluate_bash_block(block, cwd)
        finally:
            for file in expected_files:
                assert os.path.isfile(
                    file
                ), f"File {expected_files[-1]} was expected to exist *after* the test."
                os.remove(file)
