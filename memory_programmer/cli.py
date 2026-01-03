from enum import Enum

from option import Option


class CliCommand(Enum):
    READ = "read"
    WRITE = "write"


SHORT_OPTIONS = {
    "h": Option.HELP,
    "s": Option.START,
    "e": Option.END,
    "p": Option.PORT,
}


OPTION_DESCRIPTIONS = {
    Option.HELP: "print this information and exit",
    Option.START: "set the start memory address to read from or write to. Default is start of address space",
    Option.END: "set the end memory address to read from or write to. Default is end of address space",
    Option.PORT: "specify the serial port connected to the programmer",
    Option.FILE: "specify the write input or read output file"
}


def cli_print_help() -> None:
    print("usage: memory_prog.py [read | write] [options] ...")
    print("Options:")

    for option, description in OPTION_DESCRIPTIONS.items():
        try:
            short_option_index = list(SHORT_OPTIONS.values()).index(option)
            short_option = "-" + list(SHORT_OPTIONS.keys())[short_option_index] + " "
        except ValueError:
            short_option = ""

        print(f"{short_option }--{option.value} : {description}")


def cli_parse_options(cli_args: list[str]) -> dict[Option, object]:
    # Initialize all options to None, unless args provide default values.
    parsed_options = {}
    expected_option = None

    for arg in cli_args:
        if arg.startswith("-") and arg.replace("-", "").isalpha():
            option_str = arg.replace("-", "").lower()
            option = None

            if len(option_str) == 1:
                # Parse short option name.
                try:
                    option = SHORT_OPTIONS[option_str]
                except KeyError:
                    print(f"error: unknown option {option_str}")
                    break
            else:
                # Parse complete option name.
                try:
                    option = Option(option_str)
                except ValueError:
                    print(f"error: unknown option {option_str}")
                    break

            if option == Option.HELP:
                parsed_options[Option.HELP] = True
                break

            if expected_option is None:
                expected_option = option
            else:
                # Two consecutive options, error. All options expect a value.
                print(f"{expected_option} expected a value")

        elif expected_option is not None:
            parsed_options[expected_option] = arg
            expected_option = None
            
    return parsed_options


def cli_parse_inputs(inputs: list[str]) -> tuple[CliCommand, dict[Option, object]] | None:
    command = None
    if len(inputs) > 0:
        try:
            command = CliCommand(inputs[0])
        except ValueError:
            pass

    option_strings = inputs if command is None else inputs[1:]
    options = cli_parse_options(option_strings)

    if len(inputs) == 0 or options.get(Option.HELP, False) != False:
        cli_print_help()
    elif command is not None:
        return (command, options)
    else:
        print(f"error: unknown command {inputs[0]}")

