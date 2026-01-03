

class CliOption:
    def __init__(self, name: str, short_name: str | None, expects_value: bool, description: str | None) -> None:
        self.name = name
        self.short_name = short_name
        self.expects_value = expects_value
        self.description = description


class CliConfig:
    def __init__(
            self, 
            executable_name: str, 
            commands: set[str],
            num_expected_args: int, 
            options: list[CliOption],
            help_option: CliOption = CliOption("help", "h", False, "show this information and exit")
    ) -> None:
        self.executable_name = executable_name
        self.commands = commands
        self.num_expected_args = num_expected_args
        self.options = options + [help_option]
        self.help_option = help_option


def cli_parse_inputs(
        inputs: list[str], 
        cli_config: CliConfig
) -> tuple[str, list[str], dict[str, object]] | None:
    command = None
    if len(inputs) > 0 and inputs[0] in cli_config.commands:
        command = inputs[0]

    num_positional_args = cli_config.num_expected_args
    positional_args = inputs[1:num_positional_args] if command is None else inputs[1:1+num_positional_args]

    option_strings = inputs[num_positional_args:] if command is None else inputs[1+num_positional_args:]
    options = cli_parse_options(option_strings, cli_config)

    if options is not None:
        if len(inputs) == 0 or options.get("help", False) != False:
            cli_print_help(cli_config)
        elif command is not None:
            return (command, positional_args, options)
        else:
            print(f"error: unknown command {inputs[0]}")


def cli_parse_options(cli_args: list[str], cli_config: CliConfig) -> dict[str, object] | None:
    parsed_options = {}
    next_value_option = None

    for arg in cli_args:
        if arg.startswith("-") and arg.replace("-", "").isalpha():
            option_str = arg.replace("-", "").lower()

            option = None
            if len(option_str) == 1:
                # Parse short option name.
                option = next((o for o in cli_config.options if o.short_name == option_str), None)
            else:
                # Parse complete option name.
                option = next((o for o in cli_config.options if o.name == option_str), None)

            if option is None:
                print(f"error: unknown option {option_str}")
                return None

            if option == cli_config.help_option:
                parsed_options[cli_config.help_option.name] = True
                break

            if next_value_option is None:
                if option.expects_value:
                    # The option expects the next input arg to be a value.
                    next_value_option = option
                else:
                    parsed_options[option.name] = True
            else:
                # Error, two consecutive options when previous option expected a value.
                print(f"{next_value_option.name} expected a value, but got another option {option.name}")
                return None

        elif next_value_option is not None:
            parsed_options[next_value_option.name] = arg
            next_value_option = None
            
    return parsed_options


def cli_print_help(cli_config: CliConfig):
    command_format = f"[{" | ".join(cli_config.commands)}] " if len(cli_config.commands) > 0 else ""
    options_format = "[options] " if len(cli_config.options) > 0 else ""
    positional_arg_format = "... " if cli_config.num_expected_args > 0 else ""

    print(f"usage: {cli_config.executable_name} {command_format}{positional_arg_format}{options_format}")
    print("options:")

    for option in cli_config.options:
        short_name = 3 * " "
        if option.short_name is not None:
            short_name = f"-{option.short_name} "
        
        description = ""
        if option.description is not None:
            description = f" : {option.description}"

        print(short_name + f"--{option.name}" + description)
