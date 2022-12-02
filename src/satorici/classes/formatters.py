__decorations = "▢•○░"


def get_decoration(indent):
    return "  " * indent + __decorations[indent % len(__decorations)] + " "


def dict_formatter(obj: dict, capitalize: bool = False, indent: int = 0):
    for key in obj.keys():
        indent_text = get_decoration(indent)
        key_text = key.capitalize() if capitalize else key
        if isinstance(obj[key], dict):
            print(indent_text + f"{key_text}:")
            dict_formatter(obj[key], capitalize, indent + 1)
        elif isinstance(obj[key], list):
            print(indent_text + f"{key_text}:")
            list_formatter(obj[key], capitalize, indent + 1)
        else:
            print(indent_text + f"{key_text}: {obj[key]}")


def list_formatter(obj: dict, capitalize: bool = False, indent: int = 0):
    for item in obj:
        indent_text = get_decoration(indent)
        if isinstance(item, dict):
            dict_formatter(item, capitalize, indent + 1)
        elif isinstance(item, list):
            list_formatter(item, capitalize, indent + 1)
        else:
            print(indent_text + str(item))


def autoformat(obj: dict, capitalize: bool = False):
    if isinstance(obj, dict):
        dict_formatter(obj, capitalize)
    elif isinstance(obj, list):
        list_formatter(obj, capitalize)
