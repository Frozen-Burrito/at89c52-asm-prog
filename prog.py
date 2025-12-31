import sys
from enum import Enum

from serial_programmer import SerialProgrammer

class Command(Enum):
    READ = 0
    WRITE = 1


class Option(Enum):
    START = 0
    END = 1
    PORT = 2
    FILE = 3
    HELP = 4


SHORT_OPTIONS = {
    "h": "help",
    "s": "start",
    "e": "end",
    "p": "port",
}

OPTION_DESCRIPTIONS = {
    "help": "print this information and exit",
    "start": "set the start memory address to read from or write to. Default is start of address space",
    "end": "set the end memory address to read from or write to. Default is end of address space",
    "port": "specify the serial port connected to the programmer",
    "file": "specify the write input or read output file"
}


ADDRESS_START = 0
ADDRESS_END = 0xFF
DEFAULT_PORT = "COM0"
DEFAULT_BITRATE = 9600


def print_help() -> None:
    print("usage: prog [read | write] [options] ...")
    print("Options:")

    for option, description in OPTION_DESCRIPTIONS.items():
        try:
            short_option_index = list(SHORT_OPTIONS.values()).index(option)
            short_option = "-" + list(SHORT_OPTIONS.keys())[short_option_index] + " "
        except ValueError:
            short_option = ""

        print(f"{short_option }--{option} : {description}")


def parse_cli_options(cli_args: list[str]) -> dict:
    options = {}
    expected_option = None

    for arg in cli_args:
        if arg.startswith("-") and arg.replace("-", "").isalpha():
            option = arg.replace("-", "")
            if len(option) == 1:
                try:
                    option = SHORT_OPTIONS[option]
                except KeyError:
                    option = None

            if option == "help":
                options[Option.HELP] = True
            elif expected_option is None:
                if option == "start":
                    expected_option = Option.START
                elif option == "end":
                    expected_option = Option.END
                elif option == "port":
                    expected_option = Option.PORT
                elif option == "file":
                    expected_option = Option.FILE
                else:
                    # Unknown option.
                    print(f"unknown option {arg}")
            else:
                # Two consecutive options, error. All options expect a value.
                print(f"{expected_option} expected a value")

        elif expected_option is not None:
            options[expected_option] = arg
            expected_option = None
            
    return options


def memory_write(options: dict) -> None:
    source_file = options.get(Option.FILE, "a.out")
    port = options.get(Option.PORT, DEFAULT_PORT)

    address_range = options_get_address_range(options)
    if address_range is None:
        return

    start, end = address_range
    print(f"Write {source_file} from {start} to {end} at port {port}")

    serial_prog = SerialProgrammer(port, DEFAULT_BITRATE, (ADDRESS_START, ADDRESS_END))
    serial_prog.open()

    is_ok = serial_prog.seek(start)
    print(f"seek ok: {is_ok}")

    serial_prog.close()


def memory_read(options) -> None:
    source_file = options.get(Option.FILE, "contents.out")
    port = options.get(Option.PORT, DEFAULT_PORT)

    address_range = options_get_address_range(options)
    if address_range is None:
        return
    start, end = address_range

    print(f"Read {source_file} from {start} to {end} at port {port}")

    serial_prog = SerialProgrammer(port, DEFAULT_BITRATE, (ADDRESS_START, ADDRESS_END))
    serial_prog.open()

    is_ok = serial_prog.seek(start)
    print(f"seek ok: {is_ok}")

    if is_ok:
        data = serial_prog.read()
        print(f"read data: {data}")

    serial_prog.close()


def options_get_address_range(options: dict) -> tuple[int, int] | None:
    start_option_value = options.get(Option.START, ADDRESS_START)
    start = address_to_int(start_option_value)
     
    end_option_value = options.get(Option.END, ADDRESS_END)
    end = address_to_int(end_option_value)

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


def address_to_int(address) -> int | None:
    is_valid = True

    try:
        address = int(address)
    except ValueError:
        print(f"address must be an integer, not {address}")
        is_valid = False

    return address if is_valid else None
    

if __name__ == "__main__":
    print(sys.argv)

    command = None
    if len(sys.argv) > 1 and (sys.argv[1] == "read" or sys.argv[1] == "write"):
        command = sys.argv[1]

    options = parse_cli_options(sys.argv[2:])
        
    if command is None or (Option.HELP in options and options[Option.HELP]):
        print_help()
    else:
        if command == "write":
            memory_write(options)
        elif command == "read":
            memory_read(options)
