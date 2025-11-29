class PCMCaptureProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.bufferSize = 1600;
        this.buffer = new Float32Array(this.bufferSize);
        this.bufferIndex = 0;
        this.isCapturing = true;
        this.port.onmessage = this.handleMessage.bind(this);
    }

    handleMessage(event) {
        const { type } = event.data;
        if (type === 'start') {
            this.isCapturing = true;
            this.bufferIndex = 0;
        } else if (type === 'stop') {
            this.isCapturing = false;
            if (this.bufferIndex > 0) {
                this.flushBuffer();
            }
        }
    }

    process(inputs) {
        if (!this.isCapturing) {
            return true;
        }
        const input = inputs[0];
        if (!input || !input[0]) {
            return true;
        }
        const samples = input[0];
        for (let i = 0; i < samples.length; i++) {
            this.buffer[this.bufferIndex++] = samples[i];
            if (this.bufferIndex >= this.bufferSize) {
                this.flushBuffer();
            }
        }
        return true;
    }

    flushBuffer() {
        const chunk = new Float32Array(this.buffer.slice(0, this.bufferIndex));
        let sum = 0;
        for (let i = 0; i < chunk.length; i++) {
            sum += chunk[i] * chunk[i];
        }
        const level = Math.sqrt(sum / chunk.length);
        this.port.postMessage({ type: 'audio', samples: chunk, level });
        this.buffer = new Float32Array(this.bufferSize);
        this.bufferIndex = 0;
    }
}

registerProcessor('pcm-capture-processor', PCMCaptureProcessor);
