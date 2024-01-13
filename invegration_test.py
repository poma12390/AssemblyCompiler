import os
import pytest
import logging

import translator
import machine


@pytest.fixture
def temp_files():
    source = "source.temp"
    input_stream = "input.txt"
    target = "output_real.test"

    # Создаем файлы перед тестом
    open(source, 'w').close()
    open(input_stream, 'w').close()
    open(target, 'w').close()

    yield source, input_stream, target

    # Удаляем файлы после теста
    os.remove(source)
    os.remove(input_stream)
    os.remove(target)


@pytest.mark.golden_test("golden/cat.yml")
def test_translator_and_machine(golden, caplog, temp_files):
    caplog.set_level(logging.INFO)

    source, input_stream, target = temp_files
    write_input_files(source, input_stream, golden)

    output_stdout = run_translator_and_machine(source, target, input_stream)
    output_code = read_output_code(target)

    assert output_code == golden.out["out_code"]
    assert output_stdout == golden.out["out_stdout"]
    assert caplog.text == golden.out["out_log"]


def write_input_files(source, input_stream, golden):
    with open(source, "w", encoding="utf-8") as file:
        file.write(golden["in_source"])
    with open(input_stream, "w", encoding="utf-8") as file:
        file.write(golden["in_stdin"])


def run_translator_and_machine(source, target, input_stream):
    with open(input_stream, 'r') as input_file, open(target, 'w') as output_file:
        translator.main(source, output_file.name)
        print("============================================================")
        machine.main(output_file.name, input_file.name)


def read_output_code(target):
    with open(target, 'rb') as file:
        code = list(file.read())
    return [code[i] * 4096 + code[i + 1] * 256 + code[i + 2] * 16 + code[i + 3] for i in range(0, len(code), 4)]
