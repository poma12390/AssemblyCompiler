#!/usr/bin/python3
import logging
import sys

from isa import *

logger = logging.getLogger("machine_logger")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class ALU:
    def __init__(self):
        self.left = 0
        self.right = 0
        self.N = 0
        self.Z = 1
        self.C = 0

    def set_flags(self, res):
        self.N = 1 if res < 0 else 0
        self.Z = 1 if res == 0 else 0

    def __str__(self):
        return f"ALU: \n" \
               f"Left: {self.left}, Right: {self.right}\n" \
               f"Flags - N: {self.N}, Z: {self.Z}, C: {self.C}"

    # Инверсия бит в строке.
    def invert_string(self, s):
        return "".join(["1" if c == "0" else "0" for c in s])

    # Преобразование знакового числа в беззнаковое.
    def to_unsigned(self, a):
        return int(self.invert_string(bin(abs(a))[2:].zfill(REAL_RANGE)), 2) + 1

    # Преобразование беззнакового числа в знаковое.
    def to_signed(self, a):
        self.C = 1 if a >= REAL_MAX else 0
        a = a if self.C == 0 else a % REAL_MAX
        return a if MAX_NUM > a >= -MAX_NUM else -self.to_unsigned(a)

    def add(self, a, b):
        a = a if a >= 0 else self.to_unsigned(a)
        b = b if b >= 0 else self.to_unsigned(b)
        return self.to_signed(a + b)

    def sub(self, a, b):
        a = a if a >= 0 else self.to_unsigned(a)
        b = b if b >= 0 else self.to_unsigned(b)
        return self.add(a, self.to_unsigned(b))

    def div(self, a):
        self.C = a % 2
        return a // 2

    # Вычисление бинарной операции.
    def calc_op(self, left, right, op_type):
        if op_type == "add":
            return self.add(left, right)
        elif op_type == "sub" or op_type == "cmp":
            return self.sub(left, right)
        raise Exception("Incorrect binary operation")

    # Вычисление унарной операции.
    def calc_nop(self, res, op_type):
        if op_type == "asl":
            return self.add(res, res)
        elif op_type == "asr":
            return self.div(res)
        elif op_type == "inc":
            return self.add(res, 1)
        elif op_type == "dec":
            return self.sub(res, 1)
        raise Exception("Incorrect unary operation")

    # Основной метод, выполняющий операцию и при необходимости изменяющий флаги.
    def calc(self, left, right, op_type, change_flags=False):
        is_left_char = True if isinstance(left, str) else False
        left = ord(left) if is_left_char else int(left)
        C = self.C

        if right is None:
            res = left
            is_right_char = False
            res = self.calc_nop(res, op_type)
        else:
            is_right_char = True if isinstance(right, str) else False
            right = ord(right) if is_right_char else int(right)
            res = self.calc_op(left, right, op_type)
        if change_flags:
            self.set_flags(res)
        else:
            self.C = C
        if is_left_char or is_right_char:
            res = chr(res)
            if is_left_char:
                left = chr(left)
        return left if op_type == "cmp" else res


class DataPath:
    registers = {"AC": 0, "AR": 0, "IP": 0, "PC": 0, "PS": 0, "DR": 0, "CR": 0}
    memory = []
    alu = ALU()

    def __init__(self):
        self.mem_size = MAX_ADDR + 1
        self.memory = [{"value": 0}] * self.mem_size
        self.registers["SP"] = STACK_P
        self.registers["AC"] = 0
        self.registers["PS"] = 2
        self.output_buffer = []

    def __str__(self):
        return f"DataPath: \n" \
               f"Registers: {self.registers}\n" \
               f"Memory Size: {self.mem_size}\n" \
               f"ALU State: {self.alu}\n" \
               f"Output Buffer: {self.output_buffer}"

    def get_reg(self, reg):
        return self.registers[reg]

    def set_reg(self, reg, val):
        self.registers[reg] = val


class ControlUnit:
    def __init__(self, program, data_path, start_address, input_data, limit):
        self.program = program
        self.data_path = data_path
        self.limit = limit
        self.instr_counter = 0  # счетчик чтобы машина не работала бесконечно

        self.sig_latch_reg("IP", start_address)
        self._tick = 0
        self.command = ""
        self._map_instruction()

        self.input_data = input_data
        self.input_pointer = 0

    # Отображение инструкций в память.
    def _map_instruction(self):
        var_len = 0
        for i in range(len(self.program)):
            arr = self.program[i]
            command = (arr[0] // 16) * 4096 + int((arr[0] % 16) * 256)
            operand = (arr[2] // 16) * 4096 + int((arr[2] % 16) * 256) + (arr[3] // 16) * 16 + int(arr[3] % 16)
            is_addr = False
            spec_code = operand // 4096
            operand = operand % 4096
            if spec_code == 2:
                is_addr = True
            if operand == 0 and command == 0 and var_len == 0 and spec_code == 0:
                continue
            elif command != 0 and var_len == 0:
                if hex_to_mnemonic[command] in nop_commands:
                    self.data_path.memory[i] = self.create_instruction(i, hex_to_mnemonic[command], None, 0, None)
                else:
                    self.data_path.memory[i] = self.create_instruction(i, hex_to_mnemonic[command], operand, 0, is_addr)
            else:
                if var_len == 0 and operand != 0 and spec_code == 1:
                    var_len = operand
                    self.data_path.memory[i] = self.create_var(i, operand)
                elif var_len != 0:
                    self.data_path.memory[i] = self.create_var(i, chr(operand))
                    var_len -= 1
                elif spec_code == 3:
                    self.data_path.memory[i] = self.create_var(i, int(operand))

    def create_instruction(self, index, opcode, operand, value, address):
        instruction = {
            'index': index,
            'opcode': opcode,
        }

        if operand is not None:
            instruction['operand'] = operand

        instruction['value'] = value

        if address is not None:
            instruction['address'] = address

        return instruction

    def create_var(self, index, value):
        return {
            'index': index,
            'value': value,
            'opcode': 'nop'
        }

    def __str__(self):
        return f"ControlUnit: \n" \
               f"Program: {self.program}\n" \
               f"DataPath: {self.data_path}\n" \
               f"Instruction Limit: {self.limit}\n" \
               f"Instruction Counter: {self.instr_counter}\n" \
               f"Command: {self.command}\n" \
               f"Input Data: {self.input_data}\n" \
               f"Input Pointer: {self.input_pointer}"

    def get_reg(self, reg):
        return self.data_path.get_reg(reg)

    # Установка значения регистра в DataPath.
    def sig_latch_reg(self, reg, val):
        self.data_path.set_reg(reg, val)

    def sig_write(self):
        self.data_path.memory[self.data_path.registers["AR"]] = {"value": self.data_path.registers["DR"]}
        if self.data_path.registers["AR"] == OUTPUT_MAP:
            self.data_path.output_buffer.append(self.data_path.registers["DR"])
            logger.info("OUTPUT " + str(self.data_path.output_buffer[-1]))

    def sig_read(self):
        self.data_path.registers["DR"] = self.data_path.memory[self.data_path.registers["AR"]]["value"]

    def calc(self, left, right, op, change_flags=False):
        res = self.data_path.alu.calc(left, right, op, change_flags)
        if change_flags:
            self.sig_latch_reg("PS", self.get_reg("PS") ^ ((self.get_reg("PS") ^ self.data_path.alu.C) & 1))
            self.sig_latch_reg(
                "PS", self.get_reg("PS") ^ ((self.get_reg("PS") ^ (self.data_path.alu.Z << 1)) & (1 << 1))
            )
            self.sig_latch_reg(
                "PS", self.get_reg("PS") ^ ((self.get_reg("PS") ^ (self.data_path.alu.N << 2)) & (1 << 2))
            )
        return res

    def __tick(self):
        self._tick += 1

    def input_instruction(self):
        data = self.input_data[self.input_pointer][1]
        self.sig_latch_reg("PS", self.get_reg("PS") | 8)  # 1 -> PS[3]
        logger.info("INPUT " + str(data))
        self.data_path.memory[INPUT_MAP] = {"value": data}  # data -> mem[IO], загрузили символ
        self.input_pointer += 1

    def tick(self):
        self._tick += 1
        if self.input_pointer < len(self.input_data) and self.input_data[self.input_pointer][0] == self.current_tick():
            self.input_instruction()

    def current_tick(self):
        return self._tick

    def command_cycle(self):
        while self.instr_counter < self.limit:
            go_next = self.decode_and_execute_instruction()
            if (self.get_reg("PS") >> 3) & 1 == 1 and (self.get_reg("PS") >> 4) & 1 == 1:
                self.process_interrupt()
            if not go_next:
                return
            self.instr_counter += 1
        if self.instr_counter >= self.limit:
            pass
            print("Limit exceeded!")

    def process_interrupt(self):
        self.sig_latch_reg("PS", self.get_reg("PS") & ~(1 << 3))
        self.sig_latch_reg("DR", self.calc(0, self.get_reg("PS"), "add"))
        self.sig_latch_reg("AR", self.calc(0, self.get_reg("SP"), "add"))
        self.tick()  # 0 -> PS[3], IP -> DR, SP -> AR

        self.sig_write()
        self.tick()  # DR -> mem[SP]

        self.sig_latch_reg("SP", self.calc(self.get_reg("SP"), 1, "sub"))
        self.sig_latch_reg("DR", self.calc(0, self.get_reg("IP"), "add"))
        self.sig_latch_reg("AR", self.calc(0, self.get_reg("SP"), "add"))
        self.tick()  # SP - 1 -> SP,  IP -> DR, SP -> AR

        self.sig_write()
        self.tick()  # DR -> mem[SP]

        self.sig_latch_reg("SP", self.calc(self.get_reg("SP"), 1, "sub"))
        self.sig_latch_reg("AR", INT_VEC)  # адрес вектора прерываний
        self.sig_read()
        self.tick()  # SP - 1 -> SP, 0 -> AR, mem[AR] -> DR

        self.sig_latch_reg("IP", self.calc(0, self.get_reg("DR"), "add"))
        self.tick()  # DR -> IP

        self.command_cycle()  # выполняем подпрограмму для прерывания

        self.sig_latch_reg("SP", self.calc(1, self.get_reg("SP"), "add"))
        self.sig_latch_reg("AR", self.calc(0, self.get_reg("SP"), "add"))
        self.sig_read()
        self.sig_latch_reg("IP", self.calc(0, self.get_reg("DR"), "add"))
        self.tick()  # SP + 1 -> SP, SP -> AR, mem[AR] -> DR, DR -> IP

        self.sig_latch_reg("SP", self.calc(1, self.get_reg("SP"), "add"))
        self.sig_latch_reg("AR", self.calc(0, self.get_reg("SP"), "add"))
        self.sig_read()

        new_int = (self.get_reg("PS") >> 3) & 1
        self.sig_latch_reg("PS", self.calc(0, self.get_reg("DR"), "add") | new_int * 8)
        self.tick()  # SP + 1 -> SP, SP -> AR, mem[AR] -> DR, DR -> PS

        if (self.get_reg("PS") >> 3) & 1 == 1 and (self.get_reg("PS") >> 4) & 1 == 1:
            self.process_interrupt()

    def addrFetch(self):
        self.sig_latch_reg("AR", self.calc(0, self.get_reg("DR"), "add"))
        self.sig_read()
        self.tick()  # CR[operand] -> DR, DR -> AR, mem[AR] -> DR

    def opFetch(self):
        self.sig_latch_reg("AR", self.calc(0, self.get_reg("DR"), "add"))
        self.sig_read()
        self.tick()  # CR[operand] -> DR, DR -> AR, mem[AR] -> DR

    def decode_and_execute_instruction(self):
        self.sig_latch_reg("AR", self.calc(0, self.get_reg("IP"), "add"))  # IP -> AR
        self.sig_latch_reg("IP", self.calc(1, self.get_reg("IP"), "add"))  # IP + 1 -> IP
        self.sig_latch_reg("CR", self.data_path.memory[self.get_reg("AR")])
        instr = self.get_reg("CR")

        opcode = instr["opcode"]
        self.command = opcode
        self.tick()  # IP -> AR, IP + 1 -> IP, mem[AR] -> DR, DR -> CR

        if "opcode" not in instr.keys():
            return False

        # адресная команда
        if "operand" in instr.keys():
            # в DR лежит адрес операнда или адрес адреса операнда
            self.sig_latch_reg("DR", int(self.get_reg("CR")["operand"]))  # CR -> alu -> DR (operand only)

            # цикл выборки адреса
            if instr["address"]:
                self.addrFetch()

            # цикл выборки операнда
            self.opFetch()

            if opcode == "load":
                self.sig_latch_reg("AC", self.calc(0, self.get_reg("DR"), "add", True))
                self.tick()  # DR -> AC

            elif opcode == "store":
                self.sig_latch_reg("DR", self.calc(0, self.get_reg("AC"), "add"))
                self.sig_write()
                self.tick()  # AC -> DR, DR -> mem[AR]

            elif opcode in branch_commands:
                ind = branch_commands.index(opcode)
                flag = branch_flags[ind]
                condition = True

                if (flag is not None) and flag[0] == "!":
                    condition = eval("not self.data_path.alu." + flag[1])
                elif flag is not None:
                    condition = eval("self.data_path.alu." + flag[0])
                if condition:
                    self.sig_latch_reg("IP", self.calc(0, self.get_reg("AR"), "add"))
                    self.tick()  # AR -> IP
                else:
                    self.tick()  # NOP
            else:
                # арифметическая операция
                self.sig_latch_reg("AC", self.calc(self.get_reg("AC"), self.get_reg("DR"), opcode, True))
                self.tick()
        # безадресная команда
        else:
            if opcode == "hlt":
                self.tick()  # END
                return False
            elif opcode == "iret":
                self.tick()  # return
                return False
            elif opcode == "push":
                self.sig_latch_reg("DR", self.calc(self.get_reg("AC"), 0, "add"))  # AC -> DR
                self.sig_latch_reg("AR", self.calc(self.get_reg("SP"), 0, "add"))  # SP -> AR
                self.sig_latch_reg("SP", self.calc(self.get_reg("SP"), 1, "sub"))  # SP - 1 -> SP
                self.sig_write()
                self.tick()  # AC -> DR, SP -> AR, SP - 1 -> SP, DR -> mem[SP]
            elif opcode == "pop":
                self.sig_latch_reg("SP", self.calc(self.get_reg("SP"), 1, "add"))  # SP + 1 -> SP
                self.sig_latch_reg("AR", self.calc(self.get_reg("SP"), 0, "add"))  # SP -> AR
                self.sig_read()
                self.sig_latch_reg("AC", self.calc(self.get_reg("DR"), 0, "add", True))  # DR -> AC
                self.tick()  # SP + 1 -> SP, SP -> AR, mem[SP] -> DR, DR -> AC

            elif opcode == "di":
                self.sig_latch_reg("PS", self.get_reg("PS") & ~(1 << 4))
                self.tick()  # 0 -> PS[4] interrupt block
            elif opcode == "ei":
                self.sig_latch_reg("PS", self.get_reg("PS") | 16)
                self.tick()  # 1 -> PS[4] interrupt unlock
            elif opcode == "cla":
                self.sig_latch_reg("AC", self.calc(self.get_reg("AC"), self.get_reg("AC"), "sub", True))
                self.tick()  # 0 -> AC
            elif opcode == "nop":
                self.tick()  # NOP
            else:
                # унарная арифметическая операция
                self.sig_latch_reg("AC", self.calc(self.get_reg("AC"), None, opcode, True))
                self.tick()
        logger.info("\n")
        self.__print__("")
        return True  # executed successfully

    # Вспомогательный метод для отображения символов.
    def __print_symb__(self, text):
        return str((lambda x: ord(x) if isinstance(x, str) else x)(text))

    def __print__(self, comment):
        state_repr = (
            "Command: {:4} | AC {:7} | IP: {:4} | AR: {:4} | PS: {:3} | DR: {:7} | SP : {:4} | mem[AR] {:7} | "
            "mem[SP] : {:3} | CR: {:12} |"
        ).format(
            self.command,
            self.__print_symb__(self.get_reg("AC")),
            str(self.get_reg("IP")),
            str(self.get_reg("AR")),
            str(bin(self.get_reg("PS"))[2:].zfill(5)),
            self.__print_symb__(self.get_reg("DR")),
            str(self.get_reg("SP")),
            self.__print_symb__(self.data_path.memory[self.get_reg("AR")]["value"]),
            self.__print_symb__(self.data_path.memory[self.get_reg("SP")]["value"]),
            self.get_reg("CR")["opcode"]
            + (lambda x: " " + str(x["operand"]) if "operand" in x.keys() else "")(self.get_reg("CR")),
        )
        logger.info(state_repr + " " + comment)


def simulation(code, limit, input_data, start_addr):
    start_address = start_addr
    data_path = DataPath()
    control_unit = ControlUnit(code, data_path, start_address, input_data, limit)
    control_unit.command_cycle()
    return [control_unit.data_path.output_buffer, control_unit.instr_counter, control_unit.current_tick()]


def main(code, input_f):
    with open(input_f, encoding="utf-8") as file:
        input_text = file.read()
        if not input_text:
            input_token = [(-1, -1)]
        else:
            input_token = eval(input_text)  # массив с парой символ-тик
    start_addr, code = read_code(code)
    output, instr_num, ticks = simulation(
        code,
        limit=1500,
        input_data=input_token,
        start_addr=start_addr,
    )
    print(f"Output: {output}\nInstruction number: {instr_num}\nTicks: {ticks - 1}")


if __name__ == "__main__":
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    d = DataPath()
    main(code_file, input_file)
