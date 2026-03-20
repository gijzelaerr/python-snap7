"""Tests for the multi-variable read optimizer."""

from __future__ import annotations

import random
import time
from ctypes import c_char
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from snap7.client import Client
    from snap7.server import Server

from snap7.optimizer import (
    ReadItem,
    ReadBlock,
    ReadPacket,
    sort_items,
    merge_items,
    packetize,
    extract_results,
)
from snap7.type import Area, SrvArea


# ---------------------------------------------------------------------------
# Unit tests for sort_items
# ---------------------------------------------------------------------------


class TestSortItems:
    """Tests for sort_items()."""

    def test_different_areas(self) -> None:
        items = [
            ReadItem(area=0x84, db_number=1, byte_offset=0, bit_offset=0, byte_length=4, index=0),
            ReadItem(area=0x83, db_number=0, byte_offset=0, bit_offset=0, byte_length=4, index=1),
        ]
        result = sort_items(items)
        assert result[0].area == 0x83  # MK before DB
        assert result[1].area == 0x84

    def test_same_area_different_db(self) -> None:
        items = [
            ReadItem(area=0x84, db_number=2, byte_offset=0, bit_offset=0, byte_length=4, index=0),
            ReadItem(area=0x84, db_number=1, byte_offset=0, bit_offset=0, byte_length=4, index=1),
        ]
        result = sort_items(items)
        assert result[0].db_number == 1
        assert result[1].db_number == 2

    def test_same_offset_different_sizes(self) -> None:
        items = [
            ReadItem(area=0x84, db_number=1, byte_offset=0, bit_offset=0, byte_length=2, index=0),
            ReadItem(area=0x84, db_number=1, byte_offset=0, bit_offset=0, byte_length=8, index=1),
        ]
        result = sort_items(items)
        # Larger item first (descending byte_length)
        assert result[0].byte_length == 8
        assert result[1].byte_length == 2

    def test_original_not_modified(self) -> None:
        items = [
            ReadItem(area=0x84, db_number=2, byte_offset=0, bit_offset=0, byte_length=4, index=0),
            ReadItem(area=0x84, db_number=1, byte_offset=0, bit_offset=0, byte_length=4, index=1),
        ]
        sort_items(items)
        assert items[0].db_number == 2  # Original unchanged


# ---------------------------------------------------------------------------
# Unit tests for merge_items
# ---------------------------------------------------------------------------


class TestMergeItems:
    """Tests for merge_items()."""

    def test_contiguous_merge(self) -> None:
        items = sort_items(
            [
                ReadItem(area=0x84, db_number=1, byte_offset=0, bit_offset=0, byte_length=4, index=0),
                ReadItem(area=0x84, db_number=1, byte_offset=4, bit_offset=0, byte_length=4, index=1),
            ]
        )
        blocks = merge_items(items)
        assert len(blocks) == 1
        assert blocks[0].start_offset == 0
        assert blocks[0].byte_length == 8

    def test_gap_merge(self) -> None:
        items = sort_items(
            [
                ReadItem(area=0x84, db_number=1, byte_offset=0, bit_offset=0, byte_length=4, index=0),
                ReadItem(area=0x84, db_number=1, byte_offset=8, bit_offset=0, byte_length=4, index=1),
            ]
        )
        blocks = merge_items(items, max_gap=5)
        assert len(blocks) == 1
        assert blocks[0].byte_length == 12

    def test_gap_split(self) -> None:
        items = sort_items(
            [
                ReadItem(area=0x84, db_number=1, byte_offset=0, bit_offset=0, byte_length=4, index=0),
                ReadItem(area=0x84, db_number=1, byte_offset=100, bit_offset=0, byte_length=4, index=1),
            ]
        )
        blocks = merge_items(items, max_gap=5)
        assert len(blocks) == 2

    def test_different_areas_split(self) -> None:
        items = sort_items(
            [
                ReadItem(area=0x83, db_number=0, byte_offset=0, bit_offset=0, byte_length=4, index=0),
                ReadItem(area=0x84, db_number=1, byte_offset=0, bit_offset=0, byte_length=4, index=1),
            ]
        )
        blocks = merge_items(items)
        assert len(blocks) == 2

    def test_max_block_size_split(self) -> None:
        items = sort_items(
            [
                ReadItem(area=0x84, db_number=1, byte_offset=0, bit_offset=0, byte_length=300, index=0),
                ReadItem(area=0x84, db_number=1, byte_offset=300, bit_offset=0, byte_length=300, index=1),
            ]
        )
        blocks = merge_items(items, max_block_size=400)
        assert len(blocks) == 2

    def test_overlapping_items(self) -> None:
        items = sort_items(
            [
                ReadItem(area=0x84, db_number=1, byte_offset=0, bit_offset=0, byte_length=10, index=0),
                ReadItem(area=0x84, db_number=1, byte_offset=5, bit_offset=0, byte_length=10, index=1),
            ]
        )
        blocks = merge_items(items)
        assert len(blocks) == 1
        assert blocks[0].start_offset == 0
        assert blocks[0].byte_length == 15  # 0..15

    def test_empty_input(self) -> None:
        assert merge_items([]) == []


# ---------------------------------------------------------------------------
# Unit tests for packetize
# ---------------------------------------------------------------------------


class TestPacketize:
    """Tests for packetize()."""

    def test_single_block_one_packet(self) -> None:
        blocks = [ReadBlock(area=0x84, db_number=1, start_offset=0, byte_length=10, items=[])]
        packets = packetize(blocks, pdu_size=480)
        assert len(packets) == 1
        assert len(packets[0].blocks) == 1

    def test_multiple_blocks_one_packet(self) -> None:
        blocks = [
            ReadBlock(area=0x84, db_number=1, start_offset=0, byte_length=10, items=[]),
            ReadBlock(area=0x84, db_number=2, start_offset=0, byte_length=10, items=[]),
        ]
        packets = packetize(blocks, pdu_size=480)
        assert len(packets) == 1
        assert len(packets[0].blocks) == 2

    def test_request_budget_limit(self) -> None:
        # Request overhead: 14 + 12*N. With pdu=60, max blocks = (60-14)/12 = 3
        blocks = [ReadBlock(area=0x84, db_number=i, start_offset=0, byte_length=2, items=[]) for i in range(5)]
        packets = packetize(blocks, pdu_size=60)
        assert len(packets) >= 2

    def test_reply_budget_limit(self) -> None:
        # Reply overhead: 14 + sum(4 + ceil_even(length)).
        # Each block of 100 bytes costs 4+100=104 in reply.
        # With pdu=240: budget = 240-14 = 226. Fits 2 blocks (208), not 3 (312).
        blocks = [ReadBlock(area=0x84, db_number=i, start_offset=0, byte_length=100, items=[]) for i in range(3)]
        packets = packetize(blocks, pdu_size=240)
        assert len(packets) == 2

    def test_oversized_block_split(self) -> None:
        # A block larger than pdu - overhead should be split at item boundaries
        items = [
            ReadItem(area=0x84, db_number=1, byte_offset=0, bit_offset=0, byte_length=200, index=0),
            ReadItem(area=0x84, db_number=1, byte_offset=200, bit_offset=0, byte_length=200, index=1),
        ]
        blocks = [ReadBlock(area=0x84, db_number=1, start_offset=0, byte_length=400, items=items)]
        # pdu=240: max single block data = 240-12-2-4 = 222
        packets = packetize(blocks, pdu_size=240)
        total_blocks = sum(len(p.blocks) for p in packets)
        assert total_blocks == 2


# ---------------------------------------------------------------------------
# Unit tests for extract_results
# ---------------------------------------------------------------------------


class TestExtractResults:
    """Tests for extract_results()."""

    def test_correct_index_mapping(self) -> None:
        item_a = ReadItem(area=0x84, db_number=1, byte_offset=0, bit_offset=0, byte_length=4, index=1)
        item_b = ReadItem(area=0x84, db_number=1, byte_offset=4, bit_offset=0, byte_length=4, index=0)
        block = ReadBlock(area=0x84, db_number=1, start_offset=0, byte_length=8, items=[item_a, item_b])
        block.buffer = bytearray(b"\x01\x02\x03\x04\x05\x06\x07\x08")
        packet = ReadPacket(blocks=[block])

        results = extract_results([packet], 2)
        assert results[0] == bytearray(b"\x05\x06\x07\x08")  # index 0 -> item_b
        assert results[1] == bytearray(b"\x01\x02\x03\x04")  # index 1 -> item_a

    def test_overlapping_items(self) -> None:
        item_a = ReadItem(area=0x84, db_number=1, byte_offset=0, bit_offset=0, byte_length=8, index=0)
        item_b = ReadItem(area=0x84, db_number=1, byte_offset=4, bit_offset=0, byte_length=4, index=1)
        block = ReadBlock(area=0x84, db_number=1, start_offset=0, byte_length=8, items=[item_a, item_b])
        block.buffer = bytearray(b"\x10\x20\x30\x40\x50\x60\x70\x80")
        packet = ReadPacket(blocks=[block])

        results = extract_results([packet], 2)
        assert results[0] == bytearray(b"\x10\x20\x30\x40\x50\x60\x70\x80")
        assert results[1] == bytearray(b"\x50\x60\x70\x80")


# ---------------------------------------------------------------------------
# Integration tests against the server
# ---------------------------------------------------------------------------


@pytest.mark.server
class TestMultiReadServer:
    """Integration tests for multi-read via server."""

    server: Server
    client: Client
    db1_data: bytearray
    db2_data: bytearray

    @classmethod
    def setup_class(cls) -> None:
        """Start a server and connect a client."""
        from snap7.server import Server as Srv
        from snap7.client import Client as Cli

        cls.server = Srv()

        cls.db1_data = bytearray(range(100))
        db1_array = (c_char * 100).from_buffer(cls.db1_data)
        cls.server.register_area(SrvArea.DB, 1, db1_array)

        cls.db2_data = bytearray(range(100, 200))
        db2_array = (c_char * 100).from_buffer(cls.db2_data)
        cls.server.register_area(SrvArea.DB, 2, db2_array)

        port = random.randint(20000, 40000)
        cls.server.start(tcp_port=port)
        time.sleep(0.2)

        cls.client = Cli()
        cls.client.connect("127.0.0.1", 0, 0, tcp_port=port)

    @classmethod
    def teardown_class(cls) -> None:
        """Stop server and disconnect client."""
        cls.client.disconnect()
        cls.server.stop()

    def test_multi_read_basic(self) -> None:
        """Read two items from DB1 and verify data."""
        items = [
            {"area": Area.DB, "db_number": 1, "start": 0, "size": 4},
            {"area": Area.DB, "db_number": 1, "start": 10, "size": 4},
        ]
        result_code, results = self.client.read_multi_vars(items)
        assert result_code == 0
        assert len(results) == 2
        assert results[0] == bytearray(self.db1_data[0:4])
        assert results[1] == bytearray(self.db1_data[10:14])

    def test_multi_read_different_dbs(self) -> None:
        """Read items from DB1 and DB2."""
        items = [
            {"area": Area.DB, "db_number": 1, "start": 0, "size": 4},
            {"area": Area.DB, "db_number": 2, "start": 0, "size": 4},
        ]
        result_code, results = self.client.read_multi_vars(items)
        assert result_code == 0
        assert results[0] == bytearray(self.db1_data[0:4])
        assert results[1] == bytearray(self.db2_data[0:4])

    def test_single_item_still_works(self) -> None:
        """A single item should use the non-optimized path."""
        items = [
            {"area": Area.DB, "db_number": 1, "start": 5, "size": 10},
        ]
        result_code, results = self.client.read_multi_vars(items)
        assert result_code == 0
        assert results[0] == bytearray(self.db1_data[5:15])

    def test_empty_items(self) -> None:
        """Empty list should return immediately."""
        result_code, results = self.client.read_multi_vars([])
        assert result_code == 0

    def test_many_items_multiple_packets(self) -> None:
        """Enough items to potentially require multiple packets with a small PDU."""
        items = [{"area": Area.DB, "db_number": 1, "start": i * 8, "size": 4} for i in range(10)]
        result_code, results = self.client.read_multi_vars(items)
        assert result_code == 0
        assert len(results) == 10
        for i in range(10):
            expected = bytearray(self.db1_data[i * 8 : i * 8 + 4])
            assert results[i] == expected, f"Mismatch at item {i}"
