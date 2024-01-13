#!/usr/bin/python3
import logging
import sys

from isa import *

labels = {}
start_address = -1
binary_data = bytearray()
instructions = 0
mnemonic = ""


def createMnemonic():
    file_path = "mnemonic.txt"
    with open(file_path, 'w') as file:
        file.write(mnemonic)


def write_mnemonic(cur_address, instruction, operand, oper_code):
    global mnemonic
    spec_code = operand // 4096
    operand = operand % 4096
    str_oper_code = str(oper_code)[2:].upper()
    operand = int_to_hex_string(operand)
    if spec_code == 2:
        operand = "#" + operand.lstrip('0')

    mnemonic += str(cur_address) + " - "
    if instruction == "add":
        mnemonic += "4000" + str_oper_code + " - " + instruction + " " + str(operand) + " | " + "AC + " + operand
    elif instruction == "load":
        mnemonic += "A000" + str_oper_code + " - " + instruction + " " + str(operand) + " | " + operand + " -> AC"
    elif instruction == "store":
        mnemonic += "E000" + str_oper_code + " - " + instruction + " " + str(operand) + " | " + "AC -> " + operand
    elif instruction == "cmp":
        mnemonic += "7000" + str_oper_code + " - " + instruction + " " + str(
            operand) + " | " + "AC - " + operand + "set flags"
    elif instruction == "hlt":
        mnemonic += "0100" + str_oper_code + " - " + instruction + " | " + "Stop"
    elif instruction == "cla":
        mnemonic += "0200" + str_oper_code + " - " + instruction + " | " + "0 -> AC"
    elif instruction == "iret":
        mnemonic += "0B00" + str_oper_code + " - " + instruction + " | " + "return"
    elif instruction == "asl":
        mnemonic += "0500" + str_oper_code + " - " + instruction + " | " + "AC[15] -> C, AC / 2 -> AC"
    elif instruction == "asr":
        mnemonic += "0600" + str_oper_code + " - " + instruction + " | " + "AC[0] -> C, AC * 2 -> AC"
    elif instruction == "inc":
        mnemonic += "0700" + str_oper_code + " - " + instruction + " | " + "AC + 1 -> AC"
    elif instruction == "dec":
        mnemonic += "0800" + str_oper_code + " - " + instruction + " | " + "AC - 1 -> AC"
    elif instruction == "push":
        mnemonic += "0C00" + str_oper_code + " - " + instruction + " | " + "AC -> -(SP)"
    elif instruction == "pop":
        mnemonic += "0A00" + str_oper_code + " - " + instruction + " | " + "(SP)+ -> AC"
    elif instruction == "di":
        mnemonic += "1000" + str_oper_code + " - " + instruction + " | " + "Prohibit interrupt"
    elif instruction == "ei":
        mnemonic += "1100" + str_oper_code + " - " + instruction + " | " + "Allow interrupt"
    elif instruction == "nop":
        mnemonic += "0000" + str_oper_code + " - " + instruction + " | " + "No operation"
    elif instruction == "jmp":
        mnemonic += "C000" + str_oper_code + " - " + instruction + " " + str(operand) + " | " + "GOTO " + operand
    elif instruction == "jmn":
        mnemonic += "F200" + str_oper_code + " - " + instruction + " " + str(
            operand) + " | " + "GOTO " + operand + " if N == 1"
    elif instruction == "jmnn":
        mnemonic += "F300" + str_oper_code + " - " + instruction + " " + str(
            operand) + " | " + "GOTO " + operand + " if N == 0"
    elif instruction == "jmz":
        mnemonic += "F000" + str_oper_code + " - " + instruction + " " + str(
            operand) + " | " + "GOTO " + operand + " if Z == 1"
    elif instruction == "jmnz":
        mnemonic += "F100" + str_oper_code + " - " + instruction + " " + str(
            operand) + " | " + "GOTO " + operand + " if Z == 0"
    elif instruction == "jmc":
        mnemonic += "F400" + str_oper_code + " - " + instruction + " " + str(
            operand) + " | " + "GOTO " + operand + " if C == 1"
    elif instruction == "jmnc":
        mnemonic += "F500" + str_oper_code + " - " + instruction + " " + str(
            operand) + " | " + "GOTO " + operand + " if Z == 0"
    mnemonic += '\n'


# Метод для разделения строки на слова с учетом кавычек и разделителя
def split_q(string, splitter=" "):
    result = []
    in_quotes = False
    current_word = ""
    for char in string:
        if char == splitter and not in_quotes:
            if current_word:
                result.append(current_word)
                current_word = ""
        elif char == "'":
            in_quotes = not in_quotes
            current_word += char
        else:
            current_word += char
    if current_word:
        result.append(current_word)
    return result


# Метод проверяет, является ли адрес прямым адресом или ссылкой на метку
def is_direct_addr(addr):
    return is_address(addr) or (addr in labels.keys())


# Метод проверяет, является ли адрес косвенным адресом
def is_indirect_addr(addr):
    return (
            addr[0] == "("
            and addr[-1] == ")"
            and (is_address(addr[1: len(addr) - 1]) or addr[1: len(addr) - 1] in labels.keys())
    )


# Метод проверяет, является ли массив строкой с командой и операндом
def is_op_command(arr):
    return len(arr) == 2 and arr[0] in op_commands and (is_direct_addr(arr[1]) or is_indirect_addr(arr[1]))


# Метод проверяет, является ли массив строкой с командой nop
def is_nop_command(arr):
    return len(arr) == 1 and arr[0] in nop_commands


# Метод возвращает непустые строки из массива
def not_empty(arr):
    return [s for s in arr if s != ""]


# Метод проверяет, является ли массив строкой с Pascal-стилем строки
def is_pstr(arr):
    str_arr = not_empty("".join(arr[1:]).split("'"))
    num_arr = not_empty(arr[0].split(","))
    return len(num_arr) == 1 and is_number(num_arr[0]) and len(str_arr) == 1 and len(str_arr[0]) == int(num_arr[0])


# Метод проверяет, является ли массив строкой с константой
def is_const_string(arr):
    return (
            len(arr) >= 2
            and is_const_label(arr[0])
            and ((is_number(arr[1]) or arr[1] in labels.keys()) or is_pstr(arr[1:]))
    )


# Метод проверяет, является ли массив строкой с меткой и адресом
def is_address_string(arr):
    return len(arr) == 2 and arr[0] == adr_label and is_address(arr[1])


# Метод создает список словарей для представления строки с командой и операндом
def make_op_command(arr, index):
    operand = 0
    if is_indirect_addr(arr[1]):
        arr[1] = arr[1][1: len(arr[1]) - 1]
        operand += 8192
    operand += int(labels[arr[1]]) if arr[1] in labels.keys() else int(arr[1])
    add_to_binary(arr[0], int_to_hex_string(operand), index)


def append_to_file(text):
    filename = 'temp.txt'
    with open(filename, 'a') as file:
        file.write('\n' + str(text) + '\n')


def int_to_hex_string(number):
    if not (0 <= number <= 0xFFFF):
        raise ValueError("Число должно быть в диапазоне от 0 до 65535 (0xFFFF).")

    # Переводим число в 16-ричную строку, убираем префикс '0x' и дополняем нулями до 4 символов
    hex_string = format(number, '04x').upper()

    return hex_string


def add_to_binary(inst, oper, index):
    global binary_data
    check_binary_data_size(index)
    hex_command = int(mnemonic_to_hex.get(inst), 16)
    hex_operand = int(oper, 16)
    write_mnemonic(index, inst, hex_operand, oper)
    binary_data = binary_data + hex_command.to_bytes(2, 'big') + hex_operand.to_bytes(2, 'big')


def place_value_to_index(value, index):
    check_binary_data_size(index)
    if is_number(value):
        hex_operand = int(value)
    elif isinstance(value, str) and len(value) == 1:
        ascii_code = ord(value)
        hex_operand = int(format(ascii_code, '02x'), 16)
    else:
        hex_operand = int(value)
    global binary_data
    binary_data = binary_data + hex_operand.to_bytes(4, 'big')


def check_binary_data_size(index):
    global instructions
    global binary_data
    while len(binary_data) / 4 < index:
        instructions += 1
        binary_data = binary_data + (int('0000', 16).to_bytes(4, 'big'))


# Метод создает список словарей для представления строки с командой nop
def make_empty_command(arr, index):
    add_to_binary(arr[0], '0000', index)


# Метод создает список словарей для представления строки с константой
def make_consts(arr, index):
    if is_pstr(arr[1:]):
        str_arr = not_empty("".join(arr[2:]).split("'"))
        str_arr = str_arr[0]
        num = int(not_empty(arr[1].split(","))[0])
        cur = 1
        lines = [{"index": index, "value": num, "opcode": "nop"}]
        place_value_to_index(4096 + num, index)
        while cur <= num:
            lines.append({"index": index + cur, "value": str_arr[cur - 1], "opcode": "nop"})
            place_value_to_index(str_arr[cur - 1], index + cur)
            cur += 1
        return lines
    operand = int(labels[arr[1]]) if arr[1] in labels.keys() else int(arr[1])
    place_value_to_index(operand + 12288, index)


# Метод преобразует массив строк с исходным кодом в список словарей инструкций
def convert_to_bin(arr, index):
    # Проверка, является ли массив комбинацией метки и команды/операнда (или константы),
    if (len(arr) >= 2 and is_code_label(arr[0]) and (
            is_op_command(arr[1:]) or is_nop_command(arr[1:])) or is_const_string(arr[1:])):
        # Если после метки идет команда, обрабатываем как команду
        if is_op_command(arr[1:]):
            make_op_command(arr[1:], index)
        # Если после метки идет константа, обрабатываем как константу
        elif is_const_string(arr[1:]):
            make_consts(arr[1:], index)
        # Если после метки идет NOP (No Operation), обрабатываем как NOP
        else:
            make_empty_command(arr[1:], index)
    # Проверка, содержит ли массив только команду или NOP без метки
    elif len(arr) <= 2 and (is_op_command(arr) or is_nop_command(arr)):
        # Если массив содержит команду, обрабатываем как команду
        if is_op_command(arr):
            make_op_command(arr, index)
        # Если массив содержит NOP, обрабатываем как NOP
        elif is_nop_command(arr):
            make_empty_command(arr, index)
    # Проверка, содержит ли массив только константу
    elif is_const_string(arr):
        make_consts(arr, index)


# Метод проверяет метки, обрабатывает их и корректирует счетчик программы
def check_labels(arr, index):
    global start_address
    lbl = arr[0]
    if is_code_label(lbl):
        lbl = lbl[: len(lbl) - 1]
        assert lbl not in labels.keys(), "Labels must be uniq " + str(lbl) + " " + str(labels.keys())
        if lbl == start_label:
            start_address = index
        labels[lbl] = index
        if is_const_string(arr[1:]) and is_pstr(arr[2:]):
            return index + int(not_empty(arr[2].split(","))[0]) + 1
        else:
            return index + 1
    else:
        if is_const_string(arr) and is_pstr(arr[1:]):
            return index + int(not_empty(arr[1].split(","))[0]) + 1
        else:
            return index + 1


# Метод транслирует текст программы
def translate(text):
    cur = 0
    sz = len(text)
    source_code = []
    for i in range(sz):
        if not text[i]:
            continue
        text[i] = split_q(text[i], ";")[0]
        line = text[i]
        source_code.append(line)
        code_str = split_q(line)
        if is_address_string(code_str):
            cur = int(code_str[1])
            continue
        cur = check_labels(code_str, cur)

    cur = 0
    for line in source_code:
        code_str = split_q(line)
        if is_address_string(code_str):
            cur = int(code_str[1])
            continue
        convert_to_bin(code_str, cur)
        cur += 1

    assert start_label in labels.keys()


# Основной метод, читающий исходный код из файла, транслирующий его и записывающий результат в другой файл
def main(code_source, code_target):
    with open(code_source, encoding="utf-8") as f:
        code_source = f.read().split("\n")
    translate(code_source)
    global binary_data
    global start_address
    global labels
    global instructions
    createMnemonic()
    write_code(code_target, start_address, binary_data)
    start_address = -1
    instructions = len(binary_data) / 4 - instructions
    labels = {}
    binary_data = bytearray()
    print("source LoC:", len(code_source), "code instr:", int(instructions))


if __name__ == "__main__":
    assert len(sys.argv) == 3, "Wrong arguments: translator.py <input_file> <target_file>"
    _, source, target = sys.argv
    main(source, target)
