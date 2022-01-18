import snap7

class Snap7Exception(Exception):
    """
    A Snap7 specific exception.
    """
    pass


class Snap7InvalidArea(Snap7Exception):
    """Raise when value is not a valid Area"""
    def __init__(self, value):
        options = str([i for i in snap7.types.Areas.__members__.values()]).strip('[]')
        self.message = f"{value} is not a valid Area. Available areas: {options}"
    
    def __str__(self) -> str:
        return self.message