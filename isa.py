import logging

branch_commands = ["jmp", "jmn", "jmnn", "jmz", "jmnz", "jmc", "jmnc"]
branch_flags = [None, "N", "!N", "Z", "!Z", "C", "!C"]
op_commands = ["add", "load", "store", "cmp"] + branch_commands
nop_commands = ["hlt", "cla", "iret", "asl", "asr", "inc", "dec", "push", "pop", "di", "ei", "nop"]

mnemonic_to_hex = {
    "add": "4000", "load": "A000", "store": "E000", "cmp": "7000",
    "hlt": "0100", "cla": "0200", "iret": "0B00", "asl": "0500", "asr": "0600", "inc": "0700", "dec": "0800",
    "push": "0C00",
    "pop": "0A00", "di": "1000", "ei": "1100", "nop": "0000",
    "jmp": "C000", "jmn": "F200", "jmnn": "F300", "jmz": "F000", "jmnz": "F100", "jmc": "F400", "jmnc": "F500"
}
hex_to_mnemonic = {int(value, 16): key for key, value in mnemonic_to_hex.items()}

NUM_RANGE = 31
ADDR_RANGE = 11
MAX_ADDR = (1 << ADDR_RANGE) - 1
MAX_NUM = 1 << NUM_RANGE  # числа от -2^31 до 2^31 - 1

REAL_MAX = MAX_NUM * 2  # 2^32
REAL_RANGE = NUM_RANGE + 1  # 32

START_ADDR = MAX_ADDR - 3
STACK_P = MAX_ADDR - 2
INPUT_MAP = MAX_ADDR - 1
OUTPUT_MAP = MAX_ADDR

INT_VEC = 0  # вектор прерываний для ВУ

adr_label = "org"
const_label = "word:"
start_label = "start"


def is_address(text):
    var = str(text)
    return all(c.isdigit() for c in var) and MAX_ADDR >= int(var) >= 0


def is_number(text):
    var = str(text)
    return all(c.isdigit() for c in var) and MAX_NUM > int(var) >= -MAX_ADDR


def is_const_label(text):
    return text == const_label


def is_char_sym(sym):
    return ("a" <= sym <= "z") or ("A" <= sym <= "Z")


def is_sym(sym):
    return "0" <= sym <= "9" or is_char_sym(sym) or sym == "_"


def is_code_label(text):
    if not is_char_sym(text[0]):
        return False
    return (
            (text[-1] == ":")
            and text not in op_commands
            and all(is_sym(c) for c in text[:-1])
            and not (is_const_label(text))
    )


def read_code(filename):
    chunk_size = 4
    chunks = []

    with open(filename, 'rb') as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            chunks.append(list(chunk))
    start_addr = int(chunks[0][1]) * 256 + int(chunks[0][2]) * 16 + int(chunks[0][3])
    return start_addr, chunks[1:]



def append_to_file(text):
    filename = 'temp.txt'
    with open(filename, 'a') as file:
        file.write('\n' + str(text) + '\n')


def write_code(code_target, start_address, binary_data):
    binary_data = int(start_address).to_bytes(4) + binary_data
    with open(code_target, 'wb') as binary_file:
        binary_file.write(binary_data)
