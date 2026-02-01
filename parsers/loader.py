from parsers.flex_parser import FlexParser

# Future parsers add here
PARSERS = {
    "flex": FlexParser,
    # "uv": UVParser,
    # "eco": EcoParser,
}


def load_parser(machine_type: str):
    machine_type = (machine_type or "flex").lower()

    if machine_type not in PARSERS:
        print(f"⚠️ Unknown machine_type={machine_type}, defaulting to flex")

    return PARSERS.get(machine_type, FlexParser)()
