from enum import StrEnum


from opcode_table import OpcodeTable, OperandType
from assembler_error import ErrorDetails, ErrorType


class AssemblerOption(StrEnum):
    OUTPUT_FILENAME = "out"
    HEX_FORMAT = "hex"
    OPCODE_TABLE = "isa"
    HELP = "help"


# Store multiply-defined symbols as negative in the symbol table.
MTDF = -1
symbol_table: dict[str, int] = {}

opcode_table = OpcodeTable()
assembler_errors: list[ErrorDetails] = []


def assemble_sources(sources: list[str], options: dict[AssemblerOption, object]) -> int:
    print(sources)
    print(options)
    
    opcode_table_path = str(options.get(AssemblerOption.OPCODE_TABLE, ""))
    
    # Load opcode table from file.
    opcode_table.load_from_file(opcode_table_path)
    # Load SFR symbols into symbol table.
    sfr_symbols = load_sfr_addresses("./isa/8051/sfr.csv")
    for symbol, address in sfr_symbols.items():
        symbol_table[symbol] = address

    #TODO: Handle multiple source files.
    assembly_status = 0
    for source in sources[:1]:
        assembler_errors = []

        try:
            # First pass.
            print("Read symbols")
            read_defined_symbols(source)
            print_symbol_table()
            
            # Second pass.
            if not source_has_errors():
                print("Start assembly")
                assembled_instructions = assemble_with_symbols(source)
                write_output(assembled_instructions, options)
        except FileNotFoundError:
            report_error(source, ErrorType.FILE_NOT_FOUND, 0, "")

        if source_has_errors():
            assembly_status = 1
            display_error_messages()

    return assembly_status


def load_sfr_addresses(sfr_addresses_path: str, sep: str=",") -> dict[str, int]:
    sfr_addresses = {}

    with open(sfr_addresses_path, encoding="utf-8") as sfr_description_file:
        for line in sfr_description_file:
            stripped_line = line.strip()

            if len(stripped_line) == 0 or stripped_line[0] == "#":
                # Ignore empty lines.
                continue

            sfr_description = stripped_line.split(sep)

            sfr_address = int(sfr_description[0], base=16)
            sfr_symbol = sfr_description[1].strip()

            sfr_addresses[sfr_symbol] = sfr_address
    
    return sfr_addresses


def read_defined_symbols(source_file_path: str):
    with open(source_file_path, "r", encoding="utf-8") as source_file:
        location_counter = 0
        line_number = 0

        for line in source_file:
            line_number += 1

            source_line = line.strip()
            if len(source_line) == 0 or source_line.startswith(";"):
                # Skip empty and comment lines.
                continue
            
            try:
                defined_label, mnemonic, _, operand_types = parse_source_line(source_line)

                # Store defined symbols in symbol table, if any.
                if defined_label is not None:
                    if defined_label not in symbol_table:
                        symbol_table[defined_label] = location_counter
                    else:
                        symbol_table[defined_label] = MTDF
                        # print(f"error: symbol {defined_label} defined more than once, last definition at line {line_number}")
                        report_error(source_file_path, ErrorType.MULTI_DEFINED_SYMBOL, line_number, defined_label)

                # Allow lines with label and no mnemonic.
                if len(mnemonic) > 0:
                    # Determine instruction length in bytes.
                    instruction = opcode_table.find_instruction(mnemonic, operand_types)
                    location_counter += instruction.length_bytes
            except KeyError:
                report_error(source_file_path, ErrorType.UNKNOWN_MNEMONIC, line_number, source_line)
            except StopIteration:
                report_error(source_file_path, ErrorType.OPERAND_TYPE_ERROR, line_number, source_line)
            except ValueError as e:
                print(f"Error parsing line {line_number}: {source_line}")
                print(e)


def assemble_with_symbols(source_file_path: str) -> list[bytes]:
    assembled_bytes = []

    with open(source_file_path, "r", encoding="utf-8") as source_file:
        line_number = 0
        location_counter = 0

        for line in source_file:
            line_number += 1

            source_line = line.strip()
            if len(source_line) == 0 or source_line.startswith(";"):
                # Skip empty and comment lines.
                continue

            try:
                _, mnemonic, operands, operand_types = parse_source_line(source_line) 

                try:
                    # Determine instruction length in bytes.
                    instruction = opcode_table.find_instruction(mnemonic, operand_types)
                    location_counter += instruction.length_bytes
                    
                    instruction_bytes = assemble_instruction(instruction.opcode, operands, operand_types, location_counter)
                    if len(instruction_bytes) != instruction.length_bytes:
                        print(f"error: line {line_number} assembled to {len(instruction_bytes)} bytes, but should have assembled to {instruction.length_bytes} bytes")

                    assembled_bytes.append(instruction_bytes)
                except KeyError as key_error:
                    print(f"error: unknown instruction {mnemonic} with operands {operand_types} at line {line_number}")
                    print(key_error)
                    # break
            except ValueError as value_error:
                print(f"error: parsing failed at line {line_number}: {source_line}")
                print(value_error)
                # break

    return assembled_bytes


def write_output(assembled_instructions: list[bytes], options: dict[AssemblerOption, object]):
    is_hex_format = options.get(AssemblerOption.HEX_FORMAT)
    default_file_path = "a.hex" if is_hex_format else "a.out"
    file_path = str(options.get(AssemblerOption.OUTPUT_FILENAME, default_file_path))
    mode = "w" if is_hex_format else "wb"
    encoding = "utf-8" if is_hex_format else None

    with open(file_path, mode, encoding=encoding) as output_file:
        for instruction_bytes in assembled_instructions:
            if is_hex_format:
                output_file.write(instruction_bytes.hex(" ") + "\n")

    print(f"Wrote output to {file_path}")


def infer_operand_type(operand: str) -> OperandType:
    match operand:
        case "A":
            return OperandType.ACCUMULATOR
        case "C":
            return OperandType.CARRY
        case _ if operand.replace(" ", "") == "@A+DPTR":
            return OperandType.A_DPTR
        case _ if operand.replace(" ", "") == "@A+PC":
            return OperandType.A_PC
        case "AB":
            return OperandType.AB
        case _ if operand.startswith("#"):
            return OperandType.DATA
        case _ if operand.startswith("@R") and operand[-1].isnumeric():
            return OperandType.INDIRECT
        case _ if operand.replace(" ", "") == "@DPTR":
            return OperandType.INDIRECT_DPTR
        case _ if operand == "DPTR":
            return OperandType.DPTR
        case _ if operand.startswith("R") and operand[-1].isnumeric():
            return OperandType.REGISTER
        case _ if operand.startswith("/") and "." in operand and operand[-1].isnumeric():
            return OperandType.NEGATED_BIT
        case _ if "." in operand and operand[-1].isnumeric():
            return OperandType.BIT
        case _:
            return OperandType.ADDR


def parse_source_line(line: str) -> tuple[str | None, str, list[str], tuple[OperandType, ...]]:
    remaining_line = line.split(";")[0]

    label = None 
    if ":" in remaining_line:
        label, remaining_line = remaining_line.split(":", maxsplit=1)
    
    remaining_line = remaining_line.strip()
    if " " in remaining_line:
        mnemonic, remaining_line = remaining_line.split(maxsplit=1)
        operands = [o.strip() for o in remaining_line.split(",", maxsplit=2)]
    else:
        mnemonic = remaining_line
        operands = []

    # Match expected operand types to operands.
    expected_operand_types = opcode_table.get_accepted_operand_types(mnemonic, num_operands=len(operands))
    inferred_operand_types = tuple([infer_operand_type(operand) for operand in operands])

    # Need to do some "aliasing" to better match operand types.
    # Maybe an operand is a symbol, so inferred type is ADDR.
    # In that case, if instruction expects a rel operand, it should match.
    addr_aliased_types = {OperandType.DIRECT, OperandType.ADDR16, OperandType.REL}
    # If it doesn't find a set of operand types that match, matching_operand_types will be empty.
    matching_operand_types: tuple[OperandType, ...] = tuple()
    for expected_types in expected_operand_types:
        all_types_match = True
        for expected_type, inferred_type in list(zip(expected_types, inferred_operand_types)):
            all_types_match = (expected_type == inferred_type 
                                or (inferred_type == OperandType.DATA and expected_type == OperandType.DATA16)
                                or (inferred_type == OperandType.ADDR and expected_type in addr_aliased_types))
            
            if not all_types_match:
                break
        
        if all_types_match:
            matching_operand_types = expected_types

    if len(operands) != len(matching_operand_types):
        expected_type_str = " or ".join([",".join([t.value for t in types]) for types in expected_operand_types])
        raise ValueError(f"Incorrect operand types, expected {expected_type_str} but inferred {inferred_operand_types}")

    return (label, mnemonic, operands, matching_operand_types)


def assemble_instruction(base_opcode: int, operands: list[str], operand_types: tuple[OperandType, ...], next_location_counter: int) -> bytes:
    # operand_types are the operand types expected by the opcode.
    assert len(operands) <= 3
    assert len(operands) == len(operand_types)

    opcode = base_opcode
    operand_bytes = []

    # Encode each operand as additional bytes, if necessary.
    for operand, operand_type in zip(operands, operand_types):
        match operand_type:
            case OperandType.REGISTER:
                register_number = parse_register_number(operand)
                opcode |= register_number
            case OperandType.INDIRECT:
                register_number = parse_register_number(operand.removeprefix("@"))
                opcode |= register_number
            case OperandType.DATA:
                immediate_value = parse_immediate_value(operand)
                operand_bytes.append(immediate_value)
            case OperandType.DATA16:
                # 16-bit immediate value. High bits (15-8) go first.
                immediate_value = parse_immediate_value(operand)
                operand_bytes.append((immediate_value >> 8) & 0xFF)
                operand_bytes.append(immediate_value & 0xFF)
            case OperandType.DIRECT:
                try:
                    # Try to parse direct address as int.
                    no_suffix_operand = operand.removesuffix("H")
                    base = 10 if no_suffix_operand == operand else 16
                    direct_addr = int(no_suffix_operand, base)
                    # TODO: Report error if direct address is an integer, but out of 0 - 255 range.
                    operand_bytes.append(direct_addr)
                except ValueError:
                    # Try to find direct address in symbol table.
                    symbol_value = symbol_table[operand]
                    operand_bytes.append(symbol_value)
            case OperandType.BIT:
                try:
                    # Try to parse bit address as int.
                    no_suffix_operand = operand.removesuffix("H")
                    base = 10 if no_suffix_operand == operand else 16
                    bit_addr = int(no_suffix_operand, base)
                    # TODO: Report error if direct address is an integer, but out of 0 - 255 range.
                    operand_bytes.append(bit_addr)
                except ValueError:
                    # Try to find direct address in symbol table.
                    if "." in operand:
                        symbol_name, bit_index = operand.split(".", maxsplit=1)
                        symbol_addr = symbol_table[symbol_name]
                        if symbol_addr & 0x07 == 0x00 and bit_index.isnumeric():
                            symbol_addr |= int(bit_index)
                            operand_bytes.append(symbol_addr) 
                        else:
                            raise ValueError(f"{symbol_addr} is not bit-addressable, or {bit_index} is not in range 0-7")
            case OperandType.REL:
                # Encode jump destination as 8-bit signed PC offset from the next instruction.
                symbol_value = symbol_table[operand]
                operand_bytes.append((symbol_value - next_location_counter) & 0xFF)
            case OperandType.ADDR:
                # Encode 11-bit addr in opcode 7:5 and following byte.
                symbol_value = symbol_table[operand]

                opcode |= (symbol_value >> 3) & 0xE0
                operand_bytes.append(symbol_value & 0xFF)
            case OperandType.ADDR16:
                # Encode 16-bit address in following 2 bytes.
                symbol_value = symbol_table[operand]                    
                
                operand_bytes.append((symbol_value >> 8) & 0xFF)
                operand_bytes.append(symbol_value & 0xFF)
            case OperandType.NEGATED_BIT:
                try:
                    # Try to parse bit address as int.
                    no_suffix_operand = operand.removesuffix("H").removeprefix("/")
                    base = 10 if no_suffix_operand == operand else 16
                    bit_addr = int(no_suffix_operand, base)
                    # TODO: Report error if direct address is an integer, but out of 0 - 255 range.
                    operand_bytes.append(bit_addr)
                except ValueError:
                    # Try to find direct address in symbol table.
                    if "." in operand:
                        symbol_name, bit_index = operand.removeprefix("/").split(".", maxsplit=1)
                        symbol_addr = symbol_table[symbol_name]
                        if symbol_addr & 0x07 == 0x00 and bit_index.isnumeric():
                            symbol_addr |= int(bit_index)
                            operand_bytes.append(symbol_addr) 
                        else:
                            raise ValueError(f"{symbol_addr} is not bit-addressable, or {bit_index} is not in range 0-7")

    return bytes([opcode] + operand_bytes)


def print_symbol_table():
    print("Symbol table:")
    for symbol, value in symbol_table.items():
        if value != MTDF:
            print(f"{symbol} = 0x{value:04x}")
        else:
            print(f"{symbol} was defined more than once")


def parse_register_number(operand: str) -> int:
    assert operand.startswith("R")
    assert len(operand) > 1

    return int(operand[1:])


def parse_immediate_value(operand: str) -> int:
    operand_value_str = operand.upper().removeprefix("#").removesuffix("H")
    if operand.upper()[-1] == "H":
        # If immediate value has "H" prefix, treat value as hex.
        return int(operand_value_str, base=16)
    else:
        # An immediate value with no suffix is a decimal value.
        return int(operand_value_str)


def report_error(source: str, error_type: ErrorType, line_number: int, value: str):
    assembler_errors.append(ErrorDetails(source, error_type, line_number, value))


def source_has_errors() -> bool:
    return len(assembler_errors) > 0


def display_error_messages():
    print("Assembler messages")
    for error in assembler_errors:
        prefix = f"{error.source_file}:{error.line_number}: Error:" 
        match error.error_type:
            case ErrorType.FILE_NOT_FOUND:
                print(f"{prefix} can't open {error.source_file} for reading: No such file or directory.")
            case ErrorType.UNKNOWN_MNEMONIC:
                print(f"{prefix} unrecognized opcode `{error.value}'")
            case ErrorType.OPERAND_TYPE_ERROR:
                print(f"{prefix} illegal operands `{error.value}'")
            case ErrorType.MULTI_DEFINED_SYMBOL:
                print(f"{prefix} symbol `{error.value}' is already defined")


if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser

    argument_parser = ArgumentParser(description="assemble 8051 source files")
    argument_parser.add_argument("source", help="8051 assembly source file")
    argument_parser.add_argument("-o", "--output", help="name of the output file, a.out by default", default="a.out")
    argument_parser.add_argument("-x", "--hex", help="generate hex output instead of a binary file", action="store_true")
    argument_parser.add_argument("-i", "--isa", help="specify a CSV with the opcode table")
    
    args = argument_parser.parse_args()
    assembler_options = {
        AssemblerOption.OUTPUT_FILENAME: args.output,
        AssemblerOption.HEX_FORMAT: args.hex,
        AssemblerOption.OPCODE_TABLE: args.isa
    }

    assembly_status = assemble_sources(sources=[args.source], options=assembler_options)

    sys.exit(assembly_status)
