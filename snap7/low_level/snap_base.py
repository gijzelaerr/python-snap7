class TSnapBase:
    def __init__(self):
        self.LittleEndian = True

    def SwapDWord(self, value):
        return (
            ((value & 0xFF000000) >> 24)
            | ((value & 0x00FF0000) >> 8)
            | ((value & 0x0000FF00) << 8)
            | ((value & 0x000000FF) << 24)
        )

    def SwapWord(self, value):
        return ((value & 0xFF00) >> 8) | ((value & 0x00FF) << 8)
