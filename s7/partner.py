"""Unified S7 partner for peer-to-peer communication.

Wraps :class:`snap7.partner.Partner` so that the ``s7`` package is a
drop-in replacement for ``snap7``, including partner functionality.

Usage::

    from s7 import Partner

    partner = Partner(active=True)
    partner.port = 102
    partner.r_id = 0x00000001
    partner.start_to("0.0.0.0", "192.168.1.10", 0x1300, 0x1301)
    partner.set_send_data(b"Hello")
    partner.b_send()
    partner.stop()
"""

from snap7.partner import Partner, PartnerStatus

__all__ = ["Partner", "PartnerStatus"]
