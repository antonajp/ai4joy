import pytest
import base64
from app.audio.codec import encode_pcm16_to_base64, decode_base64_to_pcm16


class TestAudioCodec:
    def test_encode_pcm16_to_base64_valid_input(self):
        pcm_data = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        encoded = encode_pcm16_to_base64(pcm_data)

        assert isinstance(encoded, str)
        assert len(encoded) > 0
        base64.b64decode(encoded)

    def test_decode_base64_to_pcm16_valid_input(self):
        pcm_data = b"\x00\x01\x02\x03\x04\x05\x06\x07"
        encoded = base64.b64encode(pcm_data).decode("utf-8")

        decoded = decode_base64_to_pcm16(encoded)

        assert isinstance(decoded, bytes)
        assert decoded == pcm_data

    def test_encode_decode_roundtrip(self):
        original_data = b"\x10\x20\x30\x40\x50\x60\x70\x80"

        encoded = encode_pcm16_to_base64(original_data)
        decoded = decode_base64_to_pcm16(encoded)

        assert decoded == original_data

    def test_encode_empty_bytes(self):
        empty_data = b""

        encoded = encode_pcm16_to_base64(empty_data)

        assert encoded == ""

    def test_decode_invalid_base64(self):
        invalid_base64 = "not!valid!base64!@#$%"

        with pytest.raises(Exception):
            decode_base64_to_pcm16(invalid_base64)
