/**
 * SwarSetu Audio Worklet Processor
 * Runs on a separate high-priority audio thread.
 * Captures raw Float32 microphone input and sends it to the main thread.
 */
class SwarSetuAudioProcessor extends AudioWorkletProcessor {
  process(inputs, outputs, parameters) {
    const input = inputs[0];
    
    // Check if input source is active and has channels
    if (input && input.length > 0) {
      const channelData = input[0]; // Get the primary mono channel
      
      if (channelData && channelData.length > 0) {
        // Send a copy of the Float32Array chunk to the main thread
        this.port.postMessage(new Float32Array(channelData));
      }
    }
    
    // Keep processor alive
    return true;
  }
}

registerProcessor('swarsetu-audio-processor', SwarSetuAudioProcessor);
