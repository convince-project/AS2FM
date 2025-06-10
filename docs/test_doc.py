from pathlib import Path
import subprocess
import pytest
from sybil import Sybil
from sybil.parsers.codeblock import PythonCodeBlockParser, CodeBlockParser

COMMAND_PREFIX = "$ "


def evaluate_bash_block(example):
    lines = example.parsed.strip().split("\n")
    output = []
    output_i = -1
    for line in lines:
        if line.startswith(COMMAND_PREFIX):
            command = lines[0].replace(COMMAND_PREFIX, "")
            print(f"{command=}")
            output = (
                subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
                .strip()
                .decode("ascii")
            )
            print(f"{output=}")
            output = [l.strip() for l in output.split("\n")]
            output_i = 0
        else:
            expected_line = line.strip()
            if len(expected_line) == 0:
                continue
            if output_i == len(output):
                output_i = -1
                continue
            if output_i == -1:
                continue
            actual_line = output[output_i]
            while len(actual_line) == 0:
                output_i += 1
                actual_line = output[output_i]
            assert actual_line == expected_line
            output_i += 1


def collect_examples():
    docs_folder_path = Path(__file__).parent / "source"
    assert docs_folder_path.exists(), f"Docs path doesn't exist: {docs_folder_path.resolve()}"

    all_rst_files = list(docs_folder_path.glob("*.rst"))
    print(f"Found {len(all_rst_files)} .rst files in docs folder.")

    # Configure Sybil
    bash_parser = CodeBlockParser(language="bash", evaluator=evaluate_bash_block)
    sybil = Sybil(
        parsers=[
            bash_parser,
            # PythonCodeBlockParser(),
        ],
        pattern="*.rst",
        path=docs_folder_path.as_posix(),
    )
    examples_list = []
    for f_path in all_rst_files:
        document_ = sybil.parse(f_path)

        examples_ = list(document_)

        examples_files = [e.path for e in examples_]
        examples_start_lines = [e.start for e in examples_]

        examples_list.extend(zip(examples_files, examples_start_lines, examples_))
    return examples_list


@pytest.mark.parametrize("file_path, line, example", collect_examples())
def test_doc_examples(file_path, line, example):
    example.evaluate()
