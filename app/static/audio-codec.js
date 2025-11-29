const AudioCodec = {
    INPUT_SAMPLE_RATE: 16000,
    OUTPUT_SAMPLE_RATE: 24000,
    BIT_DEPTH: 16,
    BYTES_PER_SAMPLE: 2,
    CHUNK_DURATION_MS: 100,

    getChunkSize() {
        return (this.INPUT_SAMPLE_RATE * this.BYTES_PER_SAMPLE * this.CHUNK_DURATION_MS) / 1000;
    },

    encodePCM16ToBase64(audioBytes) {
        if (!(audioBytes instanceof ArrayBuffer) && !(audioBytes instanceof Uint8Array)) {
            throw new Error('Expected ArrayBuffer or Uint8Array');
        }
        const bytes = audioBytes instanceof ArrayBuffer ? new Uint8Array(audioBytes) : audioBytes;
        let binary = '';
        for (let i = 0; i < bytes.length; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    },

    decodeBase64ToPCM16(encoded) {
        if (typeof encoded !== 'string') {
            throw new Error('Expected string');
        }
        const binary = atob(encoded);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        if (bytes.length % this.BYTES_PER_SAMPLE !== 0) {
            throw new Error('Invalid PCM16 format: byte count not divisible by 2');
        }
        return bytes;
    },

    float32ToPCM16(float32Array) {
        const pcm16 = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            let sample = float32Array[i];
            sample = Math.max(-1, Math.min(1, sample));
            pcm16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
        }
        return new Uint8Array(pcm16.buffer);
    },

    pcm16ToFloat32(pcm16Bytes, sampleRate = this.OUTPUT_SAMPLE_RATE) {
        const int16View = new Int16Array(
            pcm16Bytes.buffer,
            pcm16Bytes.byteOffset,
            pcm16Bytes.byteLength / 2
        );
        const float32 = new Float32Array(int16View.length);
        for (let i = 0; i < int16View.length; i++) {
            float32[i] = int16View[i] / (int16View[i] < 0 ? 0x8000 : 0x7FFF);
        }
        return { samples: float32, sampleRate };
    },

    resampleAudio(samples, fromRate, toRate) {
        if (fromRate === toRate) {
            return samples;
        }
        const ratio = fromRate / toRate;
        const newLength = Math.round(samples.length / ratio);
        const result = new Float32Array(newLength);
        for (let i = 0; i < newLength; i++) {
            const srcIndex = i * ratio;
            const srcIndexFloor = Math.floor(srcIndex);
            const srcIndexCeil = Math.min(srcIndexFloor + 1, samples.length - 1);
            const fraction = srcIndex - srcIndexFloor;
            result[i] = samples[srcIndexFloor] * (1 - fraction) + samples[srcIndexCeil] * fraction;
        }
        return result;
    },

    createAudioBuffer(audioContext, float32Samples, sampleRate) {
        const buffer = audioContext.createBuffer(1, float32Samples.length, sampleRate);
        buffer.getChannelData(0).set(float32Samples);
        return buffer;
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioCodec;
}
