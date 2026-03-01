from enum import StrEnum


from serial_programmer import SerialProgrammer


ADDRESS_START = 0
ADDRESS_END = 0xFF


class MemoryProgOption(StrEnum):
    START = "start"
    END = "end"
    PORT = "port"
    FILE = "file"


DEFAULT_PORT = "COM0"
DEFAULT_BITRATE = 9600
DEFAULT_INPUT_FILE = "a.out"
DEFAULT_OUTPUT_FILE = None


def memory_write(options: dict) -> None:
    source_file = options.get(MemoryProgOption, DEFAULT_INPUT_FILE)
    port = options.get(MemoryProgOption, DEFAULT_PORT)

    address_range = options_get_address_range(options)
    if address_range is None:
        return

    start, end = address_range
    print(f"Write {source_file} from 0x{start:02x} to 0x{end:02x} at port {port}")

    serial_prog = SerialProgrammer(port, DEFAULT_BITRATE, (ADDRESS_START, ADDRESS_END))
    serial_prog.open()

    is_ok = serial_prog.seek(start)
    print(f"seek ok: {is_ok}")

    if is_ok:
        is_ok = serial_prog.write(0xF0)
        print(f"write ok: {is_ok}")

    serial_prog.close()


def memory_read(options) -> None:
    output_file = options.get(MemoryProgOption.FILE, DEFAULT_OUTPUT_FILE)
    port = options.get(MemoryProgOption.PORT, DEFAULT_PORT)

    address_range = options_get_address_range(options)
    if address_range is None:
        return
    start, end = address_range

    print(f"Read from 0x{start:02x} to 0x{end:02x} at port {port} and write to {output_file}")

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
    start = options.get(MemoryProgOption.START)
    if start is None:
        start = ADDRESS_START

    end = options.get(MemoryProgOption.END)
    if end is None:
        end = ADDRESS_END

    address_range = None
    if start <= end:
        if ADDRESS_START <= start and end <= ADDRESS_END:
            address_range = (start, end)
        else:
            print(f"ERROR: address must be in memory space range 0x{ADDRESS_START:02x} - 0x{ADDRESS_END:02x}")
    else:
        print(f"ERROR: start address must be before end address, but {start} > {end}")

    return address_range


def hex_to_decimal(value: str) -> int:
    if value.startswith("0x"):
        return int(value, base=16)
    else:
        return int(value)


if __name__ == "__main__":
    from argparse import ArgumentParser

    argument_parser = ArgumentParser(description="read and write to a memory using a serial programmer")
    argument_parser.add_argument("command", choices=["read", "write"], help="whether to read from or write to memory")

    argument_parser.add_argument("-s", "--start", type=hex_to_decimal, help="set the start memory address to read from or write to. Default is start of address space")
    argument_parser.add_argument("-e", "--end", type=hex_to_decimal, help="set the end memory address to read from or write to. Default is end of address space")
    argument_parser.add_argument("-p", "--port", help="specify the serial port connected to the programmer")
    argument_parser.add_argument("--file", help="specify the write input or read output file")

    args = argument_parser.parse_args()
    options = {
        MemoryProgOption.START: args.start,
        MemoryProgOption.END: args.end,
        MemoryProgOption.PORT: args.port,
        MemoryProgOption.FILE: args.file
    }

    match args.command:
        case "read":
            memory_read(options)
        case "write":
            memory_write(options)
