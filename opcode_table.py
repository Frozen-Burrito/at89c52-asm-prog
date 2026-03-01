from enum import StrEnum


class OperandType(StrEnum):
    ACCUMULATOR = "A"
    CARRY = "C"
    DIRECT = "dir"
    REGISTER = "Ri"
    INDIRECT = "@Ri"
    BIT = "bit"
    NEGATED_BIT = "/bit"
    DATA = "#imm"
    DATA16 = "#imm16"
    ADDR = "addr"
    ADDR16 = "addr16"
    REL = "rel"
    DPTR = "DPTR"
    AB = "AB"
    A_DPTR = "@A+DPTR"
    A_PC = "@A+PC"
    INDIRECT_DPTR = "@DPTR"


class OpcodeTableEntry:
    def __init__(self, opcode: int, length_bytes: int, operand_types: tuple[OperandType, ...]) -> None:
        self.opcode = opcode
        self.length_bytes = length_bytes
        self.operand_types = operand_types


class OpcodeTable:
    def __init__(self) -> None:
        self.table: dict[str, list[OpcodeTableEntry]] = {}


    def load_from_file(self, path: str, sep: str=","):
        with open(path, "r", encoding="utf-8") as input_file:
            for line in input_file:
                stripped_line = line.strip()

                if len(stripped_line) == 0:
                    # Ignore empty lines.
                    continue

                mnemonic, entry = self.parse_opcode_description(stripped_line, sep=sep)
                if mnemonic not in self.table:
                    self.table[mnemonic] = []
                self.table[mnemonic].append(entry)


    def parse_opcode_description(self, line: str, sep: str) -> tuple[str, OpcodeTableEntry]:
        opcode_description = line.strip().split(sep)

        base_opcode = int(opcode_description[0], base=16)
        mnemonic = opcode_description[1].strip().upper()
        length_bytes = int(opcode_description[2].strip())
        operand_specifiers = [operand_type.strip() for operand_type in opcode_description[3:]]

        operand_types = tuple([OperandType(specifier) for specifier in operand_specifiers])

        return (mnemonic, OpcodeTableEntry(base_opcode, length_bytes, operand_types))


    def get_accepted_operand_types(self, mnemonic: str, num_operands: int) -> list[tuple[OperandType, ...]]:
        return [entry.operand_types for entry in self.table[mnemonic] if len(entry.operand_types) == num_operands]


    def find_instruction(self, mnemonic: str, operand_types: tuple[OperandType, ...]) -> OpcodeTableEntry:
        return next(filter(lambda x: x.operand_types == operand_types, self.table[mnemonic]))
