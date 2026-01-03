from enum import StrEnum


from cli import cli_parse_inputs, CliConfig, CliOption


class AssemblerOption(StrEnum):
    OUTPUT_FILENAME = "out"
    HEX_FORMAT = "hex"
    OPCODE_TABLE = "isa"
    HELP = "help"


def assemble(sources: list[str], options: dict[str, object]):
    print(sources)
    print(options)


if __name__ == "__main__":
    import sys

    cli_config = CliConfig(
        executable_name="assembler.py",
        commands=None,
        num_expected_args=1,
        options=[
            CliOption(AssemblerOption.OUTPUT_FILENAME.value, "o", True, "the name of the assembler output file, a.out by default"),
            CliOption(AssemblerOption.HEX_FORMAT.value, "x", False, "generate a UTF-8 hex file instead of a binary file"),
            CliOption(AssemblerOption.OPCODE_TABLE.value, "i", True, "specify the opcode table for assembly"),
        ]
    )

    parsed_inputs = cli_parse_inputs(sys.argv[1:], cli_config)
    if parsed_inputs is not None:
        _, positional_args, options = parsed_inputs

        assemble(sources=positional_args, options=options)
