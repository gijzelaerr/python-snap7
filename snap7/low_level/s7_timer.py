class S7Timer:
    def __init__(self, buff, position=None):
        if position is not None:
            if position + 12 >= len(buff):
                self.set_timer(buff[position : position + 16])
            else:
                self.set_timer([0] * 12)
        else:
            self.set_timer(buff)

    def set_timer(self, buff):
        if len(buff) != 12:
            self.pt = 0
            self.et = 0
        else:
            res_pt = (buff[0] << 24) + (buff[1] << 16) + (buff[2] << 8) + buff[3]
            self.pt = res_pt

            res_et = (buff[4] << 24) + (buff[5] << 16) + (buff[6] << 8) + buff[7]
            self.et = res_et

            self.input = (buff[8] & 0x01) == 0x01
            self.q = (buff[8] & 0x02) == 0x02

    @property
    def PT(self):
        return self.pt

    @property
    def ET(self):
        return self.et

    @property
    def IN(self):
        return self.input

    @property
    def Q(self):
        return self.q
