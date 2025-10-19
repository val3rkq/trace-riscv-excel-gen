
def to_int(value: str | int, base: int = 16) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    
    value_str = str(value)
    
    # hex "32'hxxxxxxxx"
    if "'h" in value_str:
        try:
            hex_value = value_str.split("'h")[1]
            if 'x' in hex_value.lower() or not hex_value:
                return None
            return int(hex_value, 16)
        except (ValueError, IndexError):
            return None
    
    # bin
    if "'b" in value_str:
        try:
            bin_value = value_str.split("'b")[1]
            if 'x' in bin_value.lower() or not bin_value:
                return None
            return int(bin_value, 2)
        except (ValueError, IndexError):
            return None
    
    # skip unknown strings
    if any(x in value_str.lower() for x in ['x', 'z']) or value_str in ['***']:
        return None
    
    # finally try to convert
    try:
        return int(value_str, base) if value_str.isnumeric() else int(value_str)
    except (ValueError, TypeError):
        return None
