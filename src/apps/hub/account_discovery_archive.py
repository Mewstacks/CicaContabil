"""Bounded decoding of retained discovery blocks; no ingestion in contingency."""
from __future__ import annotations

import zlib

from apps.hub import account_discovery_contract as contract

BLOCK_LIMIT = 256 * 1024

def decompress_block(payload: bytes, expected_size: int) -> bytes:
    """A corrupt block cannot inflate beyond the fixed per-block memory budget."""
    contract.require(type(expected_size) is int and 0 < expected_size <= BLOCK_LIMIT, "BLOCK_SIZE")
    contract.require(len(payload) <= BLOCK_LIMIT + 1024, "COMPRESSED_BLOCK_SIZE")
    decoder = zlib.decompressobj()
    raw = decoder.decompress(payload, expected_size + 1)
    contract.require(
        len(raw) == expected_size
        and decoder.eof
        and not decoder.unused_data
        and not decoder.unconsumed_tail,
        "BLOCK_ENCODING",
    )
    return raw
