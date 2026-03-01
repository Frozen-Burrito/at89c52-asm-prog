from enum import IntEnum


class ErrorType(IntEnum):
    FILE_NOT_FOUND = 0
    UNKNOWN_MNEMONIC = 1
    OPERAND_TYPE_ERROR = 2
    MULTI_DEFINED_SYMBOL = 3
    UNDEFINED_SYMBOL = 4
    OPERAND_OUT_OF_RANGE = 5
    JUMP_OUT_OF_RANGE = 6
    NON_BIT_REGISTER = 7
    INVALID_REGISTER = 8


class ErrorDetails:
    def __init__(self, source_file: str, error_type: ErrorType, line_number: int, value: str) -> None:
        self.source_file = source_file
        self.error_type = error_type
        self.line_number = line_number
        self.value = value
