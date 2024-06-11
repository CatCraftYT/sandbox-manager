def format_from_list(string: str, args: list[str]) -> list[str]:
    formatted_strings = []
    for arg in args:
        formatted_strings.append(string.format(arg))
    return formatted_strings