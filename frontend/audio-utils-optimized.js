/**
 * Optimized Audio Utilities for Voice Chat
 * Includes: fast base64 encoding, VAD, streaming
 */

// Fast blob to base64 conversion (no unnecessary resampling)
async function blobToBase64Fast(blob) {
    const reader = new FileReader();
    return new Promise((resolve, reject) => {
        reader.onload = () => {
            const result = reader.result;
            // Extract base64 from data URI
            resolve(result.split(',')[1]);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

// Simple Voice Activity Detection using RMS energy
class SimpleVAD {
    constructor(sampleRate = 16000, threshold = 0.02, silenceDuration = 800) {
        this.sampleRate = sampleRate;
        this.threshold = threshold;
        this.silenceDuration = silenceDuration;
        this.silenceStart = null;
        this.isActive = false;
        this.minSpeechDuration = 100; // Minimum 100ms to count as speech
    }

    /**
     * Analyze audio chunk for speech activity
     * Returns: { isSpeaking: bool, shouldStop: bool }
     */
    analyze(audioBuffer) {
        // Calculate RMS energy
        let sum = 0;
        for (let i = 0; i < audioBuffer.length; i++) {
            sum += audioBuffer[i] * audioBuffer[i];
        }
        const rms = Math.sqrt(sum / audioBuffer.length);

        const wasSpeaking = this.isActive;
        this.isActive = rms > this.threshold;

        if (this.isActive) {
            this.silenceStart = null;
            return { isSpeaking: true, shouldStop: false };
        }

        // If silence detected
        if (!wasSpeaking) {
            return { isSpeaking: false, shouldStop: false };
        }

        // Started silence - set timer
        if (this.silenceStart === null) {
            this.silenceStart = Date.now();
            return { isSpeaking: false, shouldStop: false };
        }

        // Check if silence duration exceeded
        const silenceDurationMs = Date.now() - this.silenceStart;
        if (silenceDurationMs > this.silenceDuration) {
            return { isSpeaking: false, shouldStop: true };
        }

        return { isSpeaking: false, shouldStop: false };
    }

    reset() {
        this.silenceStart = null;
        this.isActive = false;
    }
}

// Audio Stream Recorder with VAD
class AudioStreamRecorder {
    constructor(onChunkReady, onVADEnd) {
        this.onChunkReady = onChunkReady;
        this.onVADEnd = onVADEnd;
        this.mediaRecorder = null;
        this.stream = null;
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;
        this.vad = new SimpleVAD(16000, 0.03, 600); // 600ms silence = stop
        this.isRecording = false;
        this.audioWorklet = null;
    }

    async start() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 16000
                }
            });

            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000
            });

            // Use AnalyserNode for real-time audio analysis
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 2048;
            
            const source = this.audioContext.createMediaStreamSource(this.stream);
            source.connect(this.analyser);

            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
            this.isRecording = true;

            // Start recording with MediaRecorder for WAV output
            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: 'audio/webm'
            });

            this.chunks = [];
            this.mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) {
                    this.chunks.push(e.data);
                }
            };

            // Start VAD analysis loop
            this.analyzeAudio();
            this.mediaRecorder.start();

        } catch (err) {
            console.error('Mic access failed:', err);
            throw err;
        }
    }

    analyzeAudio() {
        if (!this.isRecording) return;

        // Get current audio data
        this.analyser.getByteFrequencyData(this.dataArray);
        
        // Convert to float for VAD
        const floatArray = new Float32Array(this.dataArray.length);
        for (let i = 0; i < this.dataArray.length; i++) {
            floatArray[i] = this.dataArray[i] / 255;
        }

        const vadResult = this.vad.analyze(floatArray);

        // Callback for VAD end
        if (vadResult.shouldStop && this.onVADEnd) {
            this.stop();
            return;
        }

        // Continue monitoring
        requestAnimationFrame(() => this.analyzeAudio());
    }

    stop() {
        this.isRecording = false;
        
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }
        
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
        
        if (this.audioContext) {
            this.audioContext.close();
        }

        // Return recorded blob
        return new Blob(this.chunks, { type: 'audio/webm' });
    }
}

// Optimized base64 encoding using TextEncoder
function optimizedBase64Encode(arrayBuffer) {
    const bytes = new Uint8Array(arrayBuffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

// Fast WebM to Base64 (no resampling)
async function webmToBase64(blob) {
    const arrayBuffer = await blob.arrayBuffer();
    return optimizedBase64Encode(arrayBuffer);
}
