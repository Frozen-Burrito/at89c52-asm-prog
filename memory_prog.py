from enum import StrEnum


from cli import cli_parse_inputs, CliConfig, CliOption
from serial_programmer import SerialProgrammer


ADDRESS_START = 0
ADDRESS_END = 0xFF


class Option(StrEnum):
    START = "start"
    END = "end"
    PORT = "port"
    FILE = "file"


DEFAULT_PORT = "COM0"
DEFAULT_BITRATE = 9600
DEFAULT_INPUT_FILE = "a.out"
DEFAULT_OUTPUT_FILE = None


def memory_write(options: dict) -> None:
    source_file = options.get(Option, DEFAULT_INPUT_FILE)
    port = options.get(Option, DEFAULT_PORT)

    address_range = options_get_address_range(options)
    if address_range is None:
        return

    start, end = address_range
    print(f"Write {source_file} from {start} to {end} at port {port}")

    serial_prog = SerialProgrammer(port, DEFAULT_BITRATE, (ADDRESS_START, ADDRESS_END))
    serial_prog.open()

    is_ok = serial_prog.seek(start)
    print(f"seek ok: {is_ok}")

    if is_ok:
        is_ok = serial_prog.write(0xF0)
        print(f"write ok: {is_ok}")

    serial_prog.close()


def memory_read(options) -> None:
    output_file = options.get(Option.FILE, DEFAULT_OUTPUT_FILE)
    port = options.get(Option.PORT, DEFAULT_PORT)

    address_range = options_get_address_range(options)
    if address_range is None:
        return
    start, end = address_range

    print(f"Read from {start} to {end} at port {port} and write to {output_file}")

    serial_prog = SerialProgrammer(port, DEFAULT_BITRATE, (ADDRESS_START, ADDRESS_END))
    serial_prog.open()

    is_ok = serial_prog.seek(start)

    if is_ok:
        data = []
        address = start
        while address <= end:
            value = serial_prog.read()

            if value is None:
                break

            data.append(value)
            address += 1

        print(f"read {end - start + 1} bytes of data:")

        formatted_data = [bytes(data[i:i+16]).hex(" ") for i in range(0, len(data), 16)]

        if output_file is not None:
            with open(output_file, "w", encoding="utf-8") as out_f:
                for line in formatted_data:
                    out_f.write(line + "\n")

            print(f"wrote memory contents to {output_file}")
        else:
            for line in formatted_data:
                print(line)
    else:
        print("memory seek address failed")

    serial_prog.close()


def options_get_address_range(options: dict) -> tuple[int, int] | None:
    start_option_value = options.get(Option.START, ADDRESS_START)
    start = to_int_or_none(start_option_value)
     
    end_option_value = options.get(Option.END, ADDRESS_END)
    end = to_int_or_none(end_option_value)

    address_range = None
    if start is not None and end is not None:
        if start <= end:
            if ADDRESS_START <= start and end <= ADDRESS_END:
                address_range = (start, end)
            else:
                print(f"address must be in range {ADDRESS_START} - {ADDRESS_END}")
        else:
            print(f"start address must be before end address")
    
    return address_range


def to_int_or_none(address) -> int | None:
    is_valid = True

    try:
        address = int(address)
    except ValueError:
        print(f"address must be an integer, not {address}")
        is_valid = False

    return address if is_valid else None


if __name__ == "__main__":
    import sys

    cli_config = CliConfig(
        "memory_prog.py", 
        commands={"read", "write"}, 
        num_expected_args=0, 
        options=[
            CliOption(Option.START.value, "s", True, "set the start memory address to read from or write to. Default is start of address space"),
            CliOption(Option.END.value, "e", True, "set the end memory address to read from or write to. Default is end of address space"),
            CliOption(Option.PORT.value, "p", True, "specify the serial port connected to the programmer"),
            CliOption(Option.FILE.value, None, True, "specify the write input or read output file")
        ]
    )
    
    parsed_command = cli_parse_inputs(sys.argv[1:], cli_config)

    if parsed_command is not None:
        command, positional_args, options = parsed_command
        print(options)

        match command:
            case "read":
                memory_read(options)
            case "write":
                memory_write(options)
