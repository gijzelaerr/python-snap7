"""
Multi-variable read optimizer for S7 communication.

Optimizes multiple scattered read requests into minimal PDU-packed S7 exchanges
by merging adjacent/overlapping reads and packing them into PDU-sized packets.

.. warning::

   This module is **experimental** and its API may change in future versions.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ReadItem:
    """A single read request from the caller.

    Attributes:
        area: S7Area value (e.g. 0x84 for DB).
        db_number: DB number (0 for non-DB areas).
        byte_offset: Start byte offset in the area.
        bit_offset: Bit offset within the byte (0 for byte-level reads).
        byte_length: Number of bytes to read.
        index: Original ordering position so results can be returned in order.
    """

    area: int
    db_number: int
    byte_offset: int
    bit_offset: int
    byte_length: int
    index: int


@dataclass
class ReadBlock:
    """A merged contiguous block of bytes to read in one address spec.

    Attributes:
        area: S7Area value.
        db_number: DB number.
        start_offset: Start byte offset of the block.
        byte_length: Total bytes to read.
        items: The ReadItems contained in this block.
    """

    area: int
    db_number: int
    start_offset: int
    byte_length: int
    items: list[ReadItem] = field(default_factory=list)
    buffer: bytearray = field(default_factory=bytearray)


@dataclass
class ReadPacket:
    """A group of ReadBlocks that fit in a single S7 PDU exchange.

    Attributes:
        blocks: The blocks in this packet.
    """

    blocks: list[ReadBlock] = field(default_factory=list)


def sort_items(items: list[ReadItem]) -> list[ReadItem]:
    """Sort read items for optimal merging.

    Items are sorted by (area, db_number, byte_offset, bit_offset, -byte_length).
    Sorting by descending byte_length ensures that when two items start at the same
    offset, the larger one comes first, which simplifies overlap handling.

    Args:
        items: List of read items to sort.

    Returns:
        New sorted list (original is not modified).
    """
    return sorted(items, key=lambda i: (i.area, i.db_number, i.byte_offset, i.bit_offset, -i.byte_length))


def merge_items(sorted_items: list[ReadItem], max_gap: int = 5, max_block_size: int = 462) -> list[ReadBlock]:
    """Merge sorted read items into contiguous blocks.

    Adjacent or overlapping items in the same area/db are merged when the gap
    between them is at most *max_gap* bytes and the resulting block does not
    exceed *max_block_size* bytes.

    Args:
        sorted_items: Items pre-sorted by :func:`sort_items`.
        max_gap: Maximum byte gap between items to still merge them.
        max_block_size: Maximum byte length of a single merged block.

    Returns:
        List of merged ReadBlocks.
    """
    if not sorted_items:
        return []

    blocks: list[ReadBlock] = []
    current = sorted_items[0]
    block = ReadBlock(
        area=current.area,
        db_number=current.db_number,
        start_offset=current.byte_offset,
        byte_length=current.byte_length,
        items=[current],
    )

    for item in sorted_items[1:]:
        block_end = block.start_offset + block.byte_length
        item_end = item.byte_offset + item.byte_length

        same_region = item.area == block.area and item.db_number == block.db_number
        gap = item.byte_offset - block_end
        new_length = max(block_end, item_end) - block.start_offset

        if same_region and gap <= max_gap and new_length <= max_block_size:
            # Merge: extend block to cover the new item
            block.byte_length = new_length
            block.items.append(item)
        else:
            # Start a new block
            blocks.append(block)
            block = ReadBlock(
                area=item.area,
                db_number=item.db_number,
                start_offset=item.byte_offset,
                byte_length=item.byte_length,
                items=[item],
            )

    blocks.append(block)
    return blocks


def _ceil_even(n: int) -> int:
    """Round up to the next even number."""
    return n + (n % 2)


def _split_block(block: ReadBlock, max_block_size: int) -> list[ReadBlock]:
    """Split an oversized block at item boundaries.

    Never tears an item across two blocks.

    Args:
        block: The block to split.
        max_block_size: Maximum byte length per sub-block.

    Returns:
        List of sub-blocks that each fit within *max_block_size*.
    """
    if block.byte_length <= max_block_size:
        return [block]

    sub_blocks: list[ReadBlock] = []
    current_items: list[ReadItem] = []
    current_start = block.items[0].byte_offset
    current_end = current_start

    for item in block.items:
        item_end = item.byte_offset + item.byte_length
        new_end = max(current_end, item_end)
        new_length = new_end - current_start

        if current_items and new_length > max_block_size:
            # Flush current sub-block
            sub_blocks.append(
                ReadBlock(
                    area=block.area,
                    db_number=block.db_number,
                    start_offset=current_start,
                    byte_length=current_end - current_start,
                    items=current_items,
                )
            )
            current_items = [item]
            current_start = item.byte_offset
            current_end = item_end
        else:
            current_items.append(item)
            current_end = new_end

    if current_items:
        sub_blocks.append(
            ReadBlock(
                area=block.area,
                db_number=block.db_number,
                start_offset=current_start,
                byte_length=current_end - current_start,
                items=current_items,
            )
        )

    return sub_blocks


def packetize(blocks: list[ReadBlock], pdu_size: int) -> list[ReadPacket]:
    """Pack blocks into PDU-sized packets.

    Two budgets are enforced per packet:
      - **Request budget**: ``12 (header) + 2 (func+count) + 12*N (address specs) <= pdu_size``
      - **Reply budget**: ``12 (header) + 2 (func+count) + sum(4 + ceil_even(length)) <= pdu_size``

    Oversized blocks are first split at item boundaries, then blocks are
    greedily packed into packets.

    Args:
        blocks: Merged read blocks.
        pdu_size: Negotiated PDU size in bytes.

    Returns:
        List of ReadPackets.
    """
    # First split any oversized blocks
    # Max data payload per block in a single-block packet
    max_single_block = pdu_size - 12 - 2 - 4  # header + param + data item header
    all_blocks: list[ReadBlock] = []
    for block in blocks:
        all_blocks.extend(_split_block(block, max_single_block))

    if not all_blocks:
        return []

    request_overhead = 14  # 12 header + 2 (func + count)
    reply_overhead = 14  # 12 header + 2 (func + count)
    addr_spec_size = 12  # per block in request

    packets: list[ReadPacket] = []
    current_packet = ReadPacket()
    current_req_used = request_overhead
    current_reply_used = reply_overhead

    for block in all_blocks:
        req_cost = addr_spec_size
        reply_cost = 4 + _ceil_even(block.byte_length)

        fits_request = current_req_used + req_cost <= pdu_size
        fits_reply = current_reply_used + reply_cost <= pdu_size

        if current_packet.blocks and (not fits_request or not fits_reply):
            # Start a new packet
            packets.append(current_packet)
            current_packet = ReadPacket()
            current_req_used = request_overhead
            current_reply_used = reply_overhead

        current_packet.blocks.append(block)
        current_req_used += req_cost
        current_reply_used += reply_cost

    if current_packet.blocks:
        packets.append(current_packet)

    return packets


def extract_results(packets: list[ReadPacket], original_count: int) -> list[bytearray]:
    """Map block buffers back to original items using offset math.

    Each block must have its ``buffer`` attribute set (a bytearray of the
    block's data as returned by the PLC) before calling this function.
    The buffer is stored as a dynamic attribute on the ReadBlock dataclass.

    Args:
        packets: Packets with block buffers populated.
        original_count: Number of original read items.

    Returns:
        List of bytearrays indexed by original ``ReadItem.index``.
    """
    results: list[bytearray] = [bytearray() for _ in range(original_count)]

    for packet in packets:
        for block in packet.blocks:
            buf = block.buffer
            for item in block.items:
                local_offset = item.byte_offset - block.start_offset
                item_data = buf[local_offset : local_offset + item.byte_length]
                results[item.index] = bytearray(item_data)

    return results
