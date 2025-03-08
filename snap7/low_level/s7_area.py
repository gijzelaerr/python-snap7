class TS7Area:
    def __init__(self, Number: int, Size: int, PData: bytes):
        self.Number = Number  # Number (only for DB)
        self.Size = Size      # Area size (in bytes)
        self.PData = PData    # Pointer to area