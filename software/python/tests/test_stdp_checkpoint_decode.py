import importlib.util
from pathlib import Path

import numpy as np


def _load_fpga_stdp_parity_module():
    repo_root = Path(__file__).resolve().parents[3]
    mod_path = repo_root / "tests" / "fpga_stdp_parity.py"
    spec = importlib.util.spec_from_file_location("fpga_stdp_parity_mod", str(mod_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module spec: {mod_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mk_word(idx: int, weight_byte: int) -> np.uint32:
    return np.uint32(((weight_byte & 0xFF) << 20) | (idx & 0xFFFFF))


def test_decode_checkpoint_words_signed_weight_matches_hls_packing():
    mod = _load_fpga_stdp_parity_module()

    # HLS packs [27:20]=signed 8-bit sign-extended from packed_weight_t.
    # With 4-bit weights, 0xFD should decode to -3 after low-nibble extraction.
    words = np.array(
        [
            _mk_word(0, 0x03),  # +3
            _mk_word(1, 0xFD),  # -3 (sign-extended 8-bit)
            _mk_word(2, 0xF8),  # -8 (sign-extended 8-bit)
        ],
        dtype=np.uint32,
    )

    flat = np.zeros(16, dtype=np.int16)
    seen = np.zeros(16, dtype=np.uint8)
    seq_err, last_idx = mod.decode_checkpoint_words_into(words, flat, seen, prev_idx=-1)

    assert seq_err == 0
    assert last_idx == 2
    assert int(flat[0]) == 3
    assert int(flat[1]) == -3
    assert int(flat[2]) == -8
    assert int(seen[0]) == 1
    assert int(seen[1]) == 1
    assert int(seen[2]) == 1


def test_infer_checkpoint_format_labels_index_only_and_packed_weight():
    mod = _load_fpga_stdp_parity_module()

    assert mod.infer_checkpoint_format(8, 0, 8) == "index-only"
    assert mod.infer_checkpoint_format(8, 2, 7) == "packed-weight"
    assert mod.infer_checkpoint_format(8, 0, 0, raw_weight_byte_nonzero=3) == "packed-weight"
    assert mod.infer_checkpoint_format(0, 0, 0) == "empty"


def test_checkpoint_payload_is_index_only_uses_format_when_present():
    mod = _load_fpga_stdp_parity_module()

    assert mod.checkpoint_payload_is_index_only({"checkpoint_format": "index-only"}) is True
    assert mod.checkpoint_payload_is_index_only({"checkpoint_format": "packed-weight"}) is False
    assert mod.checkpoint_payload_is_index_only(
        {"checkpoint_words": 8, "index_only_words": 8, "weight_byte_nonzero_raw8": 1}
    ) is False


def test_flat_weight_index_maps_known_connection_indices():
    mod = _load_fpga_stdp_parity_module()

    # in0_to_hid0 starts at offset 0, dst starts at 784, dst_size=1024.
    assert mod.flat_weight_index(0, 784) == 0
    assert mod.flat_weight_index(0, 785) == 1
    assert mod.flat_weight_index(1, 784) == 1024


def test_encode_weight_load_word_packs_low_bits_for_id13():
    mod = _load_fpga_stdp_parity_module()

    pre = 5
    post = 790
    weight = 3
    w = mod.encode_weight_load_word(pre, post, weight, id_width=13)

    assert (w & ((1 << 13) - 1)) == pre
    assert ((w >> 13) & ((1 << 13) - 1)) == post
    # For id_width=13, packed weight nibble is mapped at [29:26].
    assert ((w >> 26) & 0xF) == 3
