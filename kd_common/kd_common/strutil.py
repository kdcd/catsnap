def to_camel(s: str) -> str:
    split = s.split('_')
    return split[0]+''.join(word.capitalize() for word in split[1:])
