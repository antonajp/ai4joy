"""Unit Tests for AudioCodec Module

Tests PCM16/Base64 encoding, decoding, and audio format conversions.
"""

import pytest
from playwright.sync_api import Page


class TestAudioCodecEncoding:
    """Test AudioCodec encoding functions"""

    def test_encode_pcm16_to_base64_valid_arraybuffer(self, audio_test_page: Page):
        """Test encoding ArrayBuffer to base64"""
        result = audio_test_page.evaluate("""
            const pcm16 = window.testUtils.createTestPCM16(100);  // 100 bytes
            const encoded = AudioCodec.encodePCM16ToBase64(pcm16.buffer);

            ({
                type: typeof encoded,
                isString: typeof encoded === 'string',
                length: encoded.length,
                isValidBase64: window.testUtils.isValidBase64(encoded)
            })
        """)

        assert result["type"] == "string", "Encoded output should be string"
        assert result["isString"] is True
        assert result["length"] > 0, "Encoded string should not be empty"
        assert result["isValidBase64"] is True, "Should produce valid base64"

    def test_encode_pcm16_to_base64_valid_uint8array(self, audio_test_page: Page):
        """Test encoding Uint8Array to base64"""
        result = audio_test_page.evaluate("""
            const pcm16 = window.testUtils.createTestPCM16(200);
            const encoded = AudioCodec.encodePCM16ToBase64(pcm16);

            ({
                success: true,
                type: typeof encoded,
                length: encoded.length,
                isValidBase64: window.testUtils.isValidBase64(encoded)
            })
        """)

        assert result["success"] is True
        assert result["type"] == "string"
        assert result["length"] > 0
        assert result["isValidBase64"] is True

    def test_encode_pcm16_invalid_input_type(self, audio_test_page: Page):
        """Test encoding rejects invalid input types"""
        result = audio_test_page.evaluate("""
            try {
                AudioCodec.encodePCM16ToBase64("invalid string input");
                ({ error: null })
            } catch(e) {
                ({ error: e.message })
            }
        """)

        assert result["error"] is not None, "Should throw error for invalid input"
        assert "Expected ArrayBuffer or Uint8Array" in result["error"]

    def test_encode_empty_buffer(self, audio_test_page: Page):
        """Test encoding empty buffer"""
        result = audio_test_page.evaluate("""
            const empty = new Uint8Array(0);
            const encoded = AudioCodec.encodePCM16ToBase64(empty);

            ({ encoded: encoded, length: encoded.length })
        """)

        assert result["length"] == 0, "Empty buffer should encode to empty string"


class TestAudioCodecDecoding:
    """Test AudioCodec decoding functions"""

    def test_decode_base64_to_pcm16_valid_input(self, audio_test_page: Page):
        """Test decoding valid base64 to PCM16"""
        result = audio_test_page.evaluate("""
            const original = window.testUtils.createTestPCM16(128);
            const encoded = AudioCodec.encodePCM16ToBase64(original);
            const decoded = AudioCodec.decodeBase64ToPCM16(encoded);

            ({
                type: decoded.constructor.name,
                length: decoded.length,
                matchesOriginal: Array.from(decoded).join(',') === Array.from(original).join(',')
            })
        """)

        assert result["type"] == "Uint8Array", "Decoded output should be Uint8Array"
        assert result["length"] == 128, "Decoded length should match original"
        assert result["matchesOriginal"] is True, "Decoded data should match original"

    def test_decode_base64_invalid_input_type(self, audio_test_page: Page):
        """Test decoding rejects non-string input"""
        result = audio_test_page.evaluate("""
            try {
                AudioCodec.decodeBase64ToPCM16(12345);
                ({ error: null })
            } catch(e) {
                ({ error: e.message })
            }
        """)

        assert result["error"] is not None
        assert "Expected string" in result["error"]

    def test_decode_malformed_base64(self, audio_test_page: Page):
        """Test decoding malformed base64 string"""
        result = audio_test_page.evaluate("""
            try {
                AudioCodec.decodeBase64ToPCM16("not!valid!base64!@#$%^&*");
                ({ error: null })
            } catch(e) {
                ({ error: e.message || 'decode error' })
            }
        """)

        assert result["error"] is not None, "Should throw error for malformed base64"

    def test_decode_invalid_pcm16_format(self, audio_test_page: Page):
        """Test decoding rejects odd-byte-count (invalid PCM16)"""
        result = audio_test_page.evaluate("""
            // Create 3-byte array (not divisible by 2)
            const oddBytes = new Uint8Array([0x01, 0x02, 0x03]);
            const encoded = btoa(String.fromCharCode(...oddBytes));

            try {
                AudioCodec.decodeBase64ToPCM16(encoded);
                ({ error: null })
            } catch(e) {
                ({ error: e.message })
            }
        """)

        assert result["error"] is not None
        assert "Invalid PCM16 format" in result["error"]


class TestAudioCodecConversions:
    """Test Float32 <-> PCM16 conversion functions"""

    def test_float32_to_pcm16_conversion(self, audio_test_page: Page):
        """Test converting Float32 samples to PCM16 bytes"""
        result = audio_test_page.evaluate("""
            const float32 = new Float32Array([0.0, 0.5, -0.5, 1.0, -1.0]);
            const pcm16Bytes = AudioCodec.float32ToPCM16(float32);

            // Convert back to Int16 for verification
            const int16View = new Int16Array(
                pcm16Bytes.buffer,
                pcm16Bytes.byteOffset,
                pcm16Bytes.byteLength / 2
            );

            ({
                type: pcm16Bytes.constructor.name,
                byteLength: pcm16Bytes.byteLength,
                sampleCount: int16View.length,
                zeroValue: int16View[0],
                halfPositive: int16View[1],
                halfNegative: int16View[2],
                maxPositive: int16View[3],
                maxNegative: int16View[4]
            })
        """)

        assert result["type"] == "Uint8Array"
        assert result["byteLength"] == 10, "5 samples * 2 bytes = 10 bytes"
        assert result["sampleCount"] == 5
        assert result["zeroValue"] == 0
        assert 16000 <= result["halfPositive"] <= 16500  # ~0.5 * 32767
        assert -16500 <= result["halfNegative"] <= -16000
        assert result["maxPositive"] == 32767
        assert result["maxNegative"] == -32768

    def test_float32_to_pcm16_clamping(self, audio_test_page: Page):
        """Test that values outside [-1, 1] are clamped"""
        result = audio_test_page.evaluate("""
            const float32 = new Float32Array([2.0, -2.5, 1.5, -1.5]);
            const pcm16Bytes = AudioCodec.float32ToPCM16(float32);
            const int16View = new Int16Array(
                pcm16Bytes.buffer,
                pcm16Bytes.byteOffset,
                pcm16Bytes.byteLength / 2
            );

            ({
                sample0: int16View[0],
                sample1: int16View[1],
                sample2: int16View[2],
                sample3: int16View[3],
                allClamped: Math.abs(int16View[0]) <= 32768 &&
                           Math.abs(int16View[1]) <= 32768 &&
                           Math.abs(int16View[2]) <= 32768 &&
                           Math.abs(int16View[3]) <= 32768
            })
        """)

        assert result["allClamped"] is True, "All values should be clamped to valid range"
        assert result["sample0"] == 32767, "2.0 should clamp to max positive"
        assert result["sample1"] == -32768, "-2.5 should clamp to max negative"

    def test_pcm16_to_float32_conversion(self, audio_test_page: Page):
        """Test converting PCM16 bytes to Float32 samples"""
        result = audio_test_page.evaluate("""
            const int16Data = new Int16Array([0, 16383, -16384, 32767, -32768]);
            const pcm16Bytes = new Uint8Array(int16Data.buffer);

            const { samples, sampleRate } = AudioCodec.pcm16ToFloat32(pcm16Bytes);

            ({
                type: samples.constructor.name,
                length: samples.length,
                sampleRate: sampleRate,
                zeroValue: samples[0],
                halfPositive: samples[1],
                halfNegative: samples[2],
                maxPositive: samples[3],
                maxNegative: samples[4],
                allInRange: samples.every(s => s >= -1.0 && s <= 1.0)
            })
        """)

        assert result["type"] == "Float32Array"
        assert result["length"] == 5
        assert result["sampleRate"] == 24000, "Default should be OUTPUT_SAMPLE_RATE"
        assert abs(result["zeroValue"]) < 0.001
        assert 0.49 <= result["halfPositive"] <= 0.51
        assert -0.51 <= result["halfNegative"] <= -0.49
        assert 0.99 <= result["maxPositive"] <= 1.0
        assert -1.0 <= result["maxNegative"] <= -0.99
        assert result["allInRange"] is True

    def test_pcm16_to_float32_custom_sample_rate(self, audio_test_page: Page):
        """Test PCM16 to Float32 with custom sample rate"""
        result = audio_test_page.evaluate("""
            const int16Data = new Int16Array([0, 1000, -1000]);
            const pcm16Bytes = new Uint8Array(int16Data.buffer);

            const { samples, sampleRate } = AudioCodec.pcm16ToFloat32(pcm16Bytes, 48000);

            ({ sampleRate: sampleRate, length: samples.length })
        """)

        assert result["sampleRate"] == 48000
        assert result["length"] == 3


class TestAudioCodecRoundTrip:
    """Test round-trip conversions"""

    def test_encode_decode_roundtrip(self, audio_test_page: Page):
        """Test that encode -> decode produces original data"""
        result = audio_test_page.evaluate("""
            const original = window.testUtils.createTestPCM16(256);
            const encoded = AudioCodec.encodePCM16ToBase64(original);
            const decoded = AudioCodec.decodeBase64ToPCM16(encoded);

            ({
                lengthMatches: original.length === decoded.length,
                dataMatches: Array.from(original).join(',') === Array.from(decoded).join(',')
            })
        """)

        assert result["lengthMatches"] is True
        assert result["dataMatches"] is True

    def test_float32_pcm16_roundtrip(self, audio_test_page: Page):
        """Test Float32 -> PCM16 -> Float32 preserves data (within tolerance)"""
        result = audio_test_page.evaluate("""
            const original = window.testUtils.createTestFloat32(100);
            const pcm16Bytes = AudioCodec.float32ToPCM16(original);
            const { samples: restored } = AudioCodec.pcm16ToFloat32(pcm16Bytes, 16000);

            ({
                lengthMatches: original.length === restored.length,
                dataApproximatelyMatches: window.testUtils.compareFloat32Arrays(
                    original,
                    restored,
                    0.01  // 1% tolerance for quantization error
                )
            })
        """)

        assert result["lengthMatches"] is True
        assert result["dataApproximatelyMatches"] is True, "Data should match within tolerance"


class TestAudioCodecResampling:
    """Test audio resampling functionality"""

    def test_resample_no_change(self, audio_test_page: Page):
        """Test resampling with same rate returns original"""
        result = audio_test_page.evaluate("""
            const samples = window.testUtils.createTestFloat32(100);
            const resampled = AudioCodec.resampleAudio(samples, 16000, 16000);

            ({
                lengthMatches: samples.length === resampled.length,
                dataMatches: window.testUtils.compareFloat32Arrays(samples, resampled, 0.0001)
            })
        """)

        assert result["lengthMatches"] is True
        assert result["dataMatches"] is True

    def test_resample_downsample(self, audio_test_page: Page):
        """Test downsampling (higher rate to lower rate)"""
        result = audio_test_page.evaluate("""
            const samples = window.testUtils.createTestFloat32(480);  // 480 samples
            const resampled = AudioCodec.resampleAudio(samples, 48000, 16000);

            ({
                originalLength: samples.length,
                resampledLength: resampled.length,
                expectedLength: Math.round(480 / 3),  // 48000/16000 = 3x
                isFloat32: resampled instanceof Float32Array
            })
        """)

        assert result["isFloat32"] is True
        assert result["resampledLength"] == result["expectedLength"]
        assert result["resampledLength"] < result["originalLength"]

    def test_resample_upsample(self, audio_test_page: Page):
        """Test upsampling (lower rate to higher rate)"""
        result = audio_test_page.evaluate("""
            const samples = window.testUtils.createTestFloat32(160);  // 160 samples
            const resampled = AudioCodec.resampleAudio(samples, 16000, 24000);

            ({
                originalLength: samples.length,
                resampledLength: resampled.length,
                expectedLength: Math.round(160 * 1.5),  // 24000/16000 = 1.5x
                isFloat32: resampled instanceof Float32Array
            })
        """)

        assert result["isFloat32"] is True
        assert result["resampledLength"] == result["expectedLength"]
        assert result["resampledLength"] > result["originalLength"]


class TestAudioCodecAudioBuffer:
    """Test AudioBuffer creation"""

    def test_create_audio_buffer(self, audio_test_page: Page):
        """Test creating AudioBuffer from Float32 samples"""
        result = audio_test_page.evaluate("""
            const samples = window.testUtils.createTestFloat32(1000);
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const buffer = AudioCodec.createAudioBuffer(audioContext, samples, 16000);

            ({
                isAudioBuffer: buffer instanceof AudioBuffer,
                numberOfChannels: buffer.numberOfChannels,
                sampleRate: buffer.sampleRate,
                length: buffer.length,
                duration: buffer.duration
            })
        """)

        assert result["isAudioBuffer"] is True
        assert result["numberOfChannels"] == 1, "Should be mono"
        assert result["sampleRate"] == 16000
        assert result["length"] == 1000
        assert abs(result["duration"] - 0.0625) < 0.001  # 1000 samples / 16000 Hz = 0.0625s


class TestAudioCodecConstants:
    """Test AudioCodec constants are defined correctly"""

    def test_codec_constants(self, audio_test_page: Page):
        """Test that all codec constants are defined"""
        result = audio_test_page.evaluate("""
            ({
                INPUT_SAMPLE_RATE: AudioCodec.INPUT_SAMPLE_RATE,
                OUTPUT_SAMPLE_RATE: AudioCodec.OUTPUT_SAMPLE_RATE,
                BIT_DEPTH: AudioCodec.BIT_DEPTH,
                BYTES_PER_SAMPLE: AudioCodec.BYTES_PER_SAMPLE,
                CHUNK_DURATION_MS: AudioCodec.CHUNK_DURATION_MS
            })
        """)

        assert result["INPUT_SAMPLE_RATE"] == 16000
        assert result["OUTPUT_SAMPLE_RATE"] == 24000
        assert result["BIT_DEPTH"] == 16
        assert result["BYTES_PER_SAMPLE"] == 2
        assert result["CHUNK_DURATION_MS"] == 100

    def test_get_chunk_size(self, audio_test_page: Page):
        """Test chunk size calculation"""
        result = audio_test_page.evaluate("""
            const chunkSize = AudioCodec.getChunkSize();
            const expected = (16000 * 2 * 100) / 1000;  // 3200 bytes

            ({ chunkSize: chunkSize, expected: expected, matches: chunkSize === expected })
        """)

        assert result["matches"] is True
        assert result["chunkSize"] == 3200
