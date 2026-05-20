/**
 * SwarSetu Web Application Core Logic
 * Handles WebSocket communication, AudioContext initialization, PTT/Continuous streaming modes,
 * and real-time audio visualization.
 */

// --- Configuration & State Variables ---
let wsUrl = '';
let sampleRate = 16000;
let chunkSize = 1024;
let userInitiatedDisconnect = false;
let reconnectTimer = null;
let packetCount = 0;
let isStreaming = false;
let isConnected = false;
let mode = 'ptt'; // 'ptt' or 'stream'

// Audio system components
let audioContext = null;
let micStream = null;
let workletNode = null;
let analyserNode = null;
let pcmBuffer = [];

// DOM Elements
const pttBtn = document.getElementById('ptt-btn');
const pttPrompt = document.getElementById('ptt-prompt');
const connectBtn = document.getElementById('connect-btn');
const connectBtnText = document.getElementById('connect-btn-text');
const settingsToggleBtn = document.getElementById('settings-toggle-btn');
const settingsDrawer = document.getElementById('settings-drawer');
const settingsCloseBtn = document.getElementById('settings-close-btn');
const saveSettingsBtn = document.getElementById('save-settings-btn');
const drawerOverlay = document.getElementById('drawer-overlay');
const toastElement = document.getElementById('toast');

const connectionDot = document.getElementById('connection-dot');
const statusText = document.getElementById('status-text');
const statPackets = document.getElementById('stat-packets');
const statLatency = document.getElementById('stat-latency');
const statModeBadge = document.getElementById('stat-mode-badge');

const wsUrlInput = document.getElementById('ws-url-input');
const sampleRateSelect = document.getElementById('sample-rate-select');
const chunkSizeSelect = document.getElementById('chunk-size-select');

const diagMicPerm = document.getElementById('diag-mic-perm');
const diagAudioContext = document.getElementById('diag-audio-context');
const diagActualRate = document.getElementById('diag-actual-rate');
const canvas = document.getElementById('waveform-canvas');

// WebSocket reference
let ws = null;

// --- Initialize Settings from LocalStorage ---
function loadSettings() {
  const isHttps = window.location.protocol === 'https:';
  const defaultWsUrl = isHttps 
    ? `wss://${window.location.hostname}/ws/stream` 
    : `ws://${window.location.hostname || 'localhost'}:8000/ws/stream`;
  
  wsUrl = localStorage.getItem('swarsetu_ws_url') || defaultWsUrl;
  sampleRate = parseInt(localStorage.getItem('swarsetu_sample_rate')) || 16000;
  chunkSize = parseInt(localStorage.getItem('swarsetu_chunk_size')) || 1024;
  mode = localStorage.getItem('swarsetu_mode') || 'ptt';

  // Apply to UI fields
  wsUrlInput.value = wsUrl;
  sampleRateSelect.value = sampleRate;
  chunkSizeSelect.value = chunkSize;
  
  updateModeUI();
}

function saveSettings() {
  wsUrl = wsUrlInput.value.trim();
  sampleRate = parseInt(sampleRateSelect.value);
  chunkSize = parseInt(chunkSizeSelect.value);
  
  localStorage.setItem('swarsetu_ws_url', wsUrl);
  localStorage.setItem('swarsetu_sample_rate', sampleRate);
  localStorage.setItem('swarsetu_chunk_size', chunkSize);
  
  showToast('Settings saved. Reconnect to apply.', 'success');
  closeDrawer();
  
  // Update diagnostics display
  updateDiagnostics();
}

// --- Notification Toast ---
let toastTimeout = null;
function showToast(message, type = 'info') {
  clearTimeout(toastTimeout);
  toastElement.textContent = message;
  toastElement.className = 'toast show';
  
  if (type === 'error') {
    toastElement.classList.add('error');
  } else if (type === 'success') {
    toastElement.classList.add('success');
  }
  
  toastTimeout = setTimeout(() => {
    toastElement.classList.remove('show');
  }, 3000);
}

// --- Drawer Panels ---
function openDrawer() {
  settingsDrawer.classList.add('open');
  drawerOverlay.classList.add('open');
  updateDiagnostics();
}

function closeDrawer() {
  settingsDrawer.classList.remove('open');
  drawerOverlay.classList.remove('open');
}

// --- Diagnostics Panel ---
function updateDiagnostics() {
  // Check permission state if API is available
  if (navigator.permissions && navigator.permissions.query) {
    navigator.permissions.query({ name: 'microphone' }).then((result) => {
      if (result.state === 'granted') {
        diagMicPerm.textContent = 'Granted';
        diagMicPerm.className = 'diag-status success';
      } else if (result.state === 'prompt') {
        diagMicPerm.textContent = 'Prompt Needed';
        diagMicPerm.className = 'diag-status warning';
      } else {
        diagMicPerm.textContent = 'Denied';
        diagMicPerm.className = 'diag-status error';
      }
    }).catch(() => {
      diagMicPerm.textContent = 'Unknown';
      diagMicPerm.className = 'diag-status';
    });
  }
  
  if (audioContext) {
    diagAudioContext.textContent = audioContext.state.toUpperCase();
    diagAudioContext.className = `diag-status ${audioContext.state === 'running' ? 'success' : 'warning'}`;
    diagActualRate.textContent = `${audioContext.sampleRate} Hz`;
  } else {
    diagAudioContext.textContent = 'Not Initialized';
    diagAudioContext.className = 'diag-status';
    diagActualRate.textContent = '--';
  }
}

// --- Mode Toggle Logic ---
function setMode(newMode) {
  if (isStreaming) {
    stopVoiceStream();
  }
  mode = newMode;
  localStorage.setItem('swarsetu_mode', mode);
  updateModeUI();
}

function updateModeUI() {
  document.getElementById('mode-ptt').classList.toggle('active', mode === 'ptt');
  document.getElementById('mode-stream').classList.toggle('active', mode === 'stream');
  
  statModeBadge.textContent = mode.toUpperCase();
  statModeBadge.className = `stat-value ${mode === 'ptt' ? 'badge-ptt' : 'badge-stream'}`;
  
  updatePttButtonState();
}

function updatePttButtonState() {
  if (!isConnected) {
    pttBtn.disabled = true;
    pttBtn.className = 'ptt-button';
    pttPrompt.textContent = 'CONNECT SERVER';
    return;
  }
  
  pttBtn.disabled = false;
  
  if (isStreaming) {
    pttBtn.className = 'ptt-button streaming';
    pttPrompt.textContent = mode === 'ptt' ? 'TALKING...' : 'ON AIR';
  } else {
    pttBtn.className = 'ptt-button ready';
    pttPrompt.textContent = mode === 'ptt' ? 'HOLD TO TALK' : 'TAP TO START';
  }
}

// --- Audio Capture & Pipeline ---
async function initAudio() {
  if (audioContext) {
    // If context is suspended (browser autoplay safety), resume it
    if (audioContext.state === 'suspended') {
      await audioContext.resume();
    }
    return true;
  }
  
  try {
    // 1. Request microphone capture
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
        latency: 0
      }
    });
    
    // 2. Initialize AudioContext at target sample rate
    audioContext = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: sampleRate,
      latencyHint: 'interactive'
    });
    
    // 3. Setup analyser node for UI visualizer
    analyserNode = audioContext.createAnalyser();
    analyserNode.fftSize = 256;
    
    // 4. Load AudioWorklet. We define it as an inline Blob to avoid cross-origin (file:// or Cloudflare Page subdomains) loads blocks.
    const workletCode = `
      class SwarSetuAudioProcessor extends AudioWorkletProcessor {
        process(inputs, outputs, parameters) {
          const input = inputs[0];
          if (input && input.length > 0) {
            const channelData = input[0];
            if (channelData && channelData.length > 0) {
              // Send mono raw Float32 data to app.js thread
              this.port.postMessage(new Float32Array(channelData));
            }
          }
          return true;
        }
      }
      registerProcessor('swarsetu-audio-processor', SwarSetuAudioProcessor);
    `;
    
    const blob = new Blob([workletCode], { type: 'application/javascript' });
    const workletUrl = URL.createObjectURL(blob);
    
    await audioContext.audioWorklet.addModule(workletUrl);
    
    // 5. Connect node graph
    const sourceNode = audioContext.createMediaStreamSource(micStream);
    workletNode = new AudioWorkletNode(audioContext, 'swarsetu-audio-processor');
    
    sourceNode.connect(analyserNode);
    
    // Zero gain keeps AudioWorklet active in browser's graph without looping back to device output
    const silenceGain = audioContext.createGain();
    silenceGain.gain.value = 0.0;
    
    workletNode.connect(silenceGain);
    silenceGain.connect(audioContext.destination);
    
    sourceNode.connect(workletNode);
    
    // 6. Handle chunks incoming from Worklet thread
    workletNode.port.onmessage = handleAudioSamples;
    
    updateDiagnostics();
    return true;
  } catch (err) {
    console.error('SwarSetu Audio initialization failed:', err);
    showToast('Microphone access denied: ' + err.message, 'error');
    return false;
  }
}

function handleAudioSamples(event) {
  if (!isStreaming || !isConnected || !ws || ws.readyState !== WebSocket.OPEN) {
    return;
  }
  
  const float32Samples = event.data;
  pcmBuffer.push(...float32Samples);
  
  // Once buffered enough samples, convert and send chunk
  while (pcmBuffer.length >= chunkSize) {
    const samplesToProcess = pcmBuffer.splice(0, chunkSize);
    const pcm16Buffer = floatTo16BitPCM(samplesToProcess);
    
    try {
      const startTime = performance.now();
      ws.send(pcm16Buffer);
      packetCount++;
      statPackets.textContent = packetCount;
      
      // Rough round-trip benchmark representation (WebSocket is uni-directional here, shows instant packet transmission time)
      const transmitTime = Math.round(performance.now() - startTime);
      statLatency.textContent = `${transmitTime} ms`;
    } catch (e) {
      console.error('Error sending audio chunk:', e);
    }
  }
}

// Convert Float32 numbers [-1.0, 1.0] to Int16 signed bytes [-32768, 32767]
function floatTo16BitPCM(float32Array) {
  const buffer = new ArrayBuffer(float32Array.length * 2);
  const view = new DataView(buffer);
  
  for (let i = 0; i < float32Array.length; i++) {
    let sample = Math.max(-1.0, Math.min(1.0, float32Array[i]));
    // Convert
    view.setInt16(i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true); // true = little endian PCM
  }
  
  return buffer;
}

// --- Voice Streaming Trigger Actions ---
async function startVoiceStream() {
  if (!isConnected) return;
  if (isStreaming) return;
  
  const audioOk = await initAudio();
  if (!audioOk) return;
  
  isStreaming = true;
  pcmBuffer = []; // Clear residual audio history
  
  updatePttButtonState();
}

function stopVoiceStream() {
  if (!isStreaming) return;
  isStreaming = false;
  updatePttButtonState();
}

// --- WebSocket Connection ---
function connectServer() {
  if (isConnected || ws) return;
  
  clearTimeout(reconnectTimer);
  userInitiatedDisconnect = false;
  
  connectionDot.className = 'status-dot connecting';
  statusText.textContent = 'Connecting...';
  connectBtnText.textContent = 'Connecting...';
  connectBtn.disabled = true;
  
  // Format WSS query parameters
  let targetUrl;
  try {
    const baseUri = new URL(wsUrl);
    baseUri.searchParams.set('sampleRate', sampleRate);
    baseUri.searchParams.set('channels', 1);
    targetUrl = baseUri.toString();
  } catch (err) {
    showToast('Invalid WebSocket URL schema.', 'error');
    resetConnectionUI();
    return;
  }
  
  console.log('Connecting to SwarSetu server:', targetUrl);
  
  try {
    ws = new WebSocket(targetUrl);
    ws.binaryType = 'arraybuffer';
    
    ws.onopen = async () => {
      console.log('WebSocket connection established.');
      isConnected = true;
      connectBtn.disabled = false;
      connectBtn.className = 'action-btn connect-action connected';
      connectBtnText.textContent = 'Disconnect';
      
      connectionDot.className = 'status-dot connected';
      statusText.textContent = 'Connected';
      
      showToast('Connected to SwarSetu Bridge', 'success');
      
      // Auto-initialize audio context on connection if microphone permission was granted earlier
      await initAudio();
      
      updatePttButtonState();
    };
    
    ws.onclose = (event) => {
      console.log(`WebSocket closed. Code: ${event.code}, Reason: ${event.reason}`);
      resetConnectionUI();
      
      if (!userInitiatedDisconnect) {
        showToast('Connection lost. Reconnecting in 3s...', 'error');
        reconnectTimer = setTimeout(connectServer, 3000);
      }
    };
    
    ws.onerror = (err) => {
      console.error('WebSocket error event triggered:', err);
      showToast('Connection failed.', 'error');
    };
    
  } catch (err) {
    console.error('Failed to spawn WebSocket:', err);
    showToast('Invalid WebSocket URL.', 'error');
    resetConnectionUI();
  }
}

function disconnectServer() {
  userInitiatedDisconnect = true;
  clearTimeout(reconnectTimer);
  
  if (isStreaming) {
    stopVoiceStream();
  }
  
  if (ws) {
    ws.close();
    ws = null;
  }
  
  resetConnectionUI();
  showToast('Disconnected from server.', 'info');
}

function resetConnectionUI() {
  isConnected = false;
  isStreaming = false;
  ws = null;
  
  connectionDot.className = 'status-dot disconnected';
  statusText.textContent = 'Disconnected';
  
  connectBtn.disabled = false;
  connectBtn.className = 'action-btn connect-action';
  connectBtnText.textContent = 'Connect Server';
  
  packetCount = 0;
  statPackets.textContent = '0';
  statLatency.textContent = '-- ms';
  
  updatePttButtonState();
}

// --- Canvas Visualizer Animation loop ---
function renderVisualizer() {
  requestAnimationFrame(renderVisualizer);
  
  const width = canvas.width = canvas.clientWidth;
  const height = canvas.height = canvas.clientHeight;
  const ctx = canvas.getContext('2d');
  
  ctx.clearRect(0, 0, width, height);
  
  let bufferLength = 0;
  let dataArray = null;
  
  // Get time domain data from microphone analyser if actively connected and streaming
  if (analyserNode && isStreaming) {
    bufferLength = analyserNode.frequencyBinCount;
    dataArray = new Uint8Array(bufferLength);
    analyserNode.getByteTimeDomainData(dataArray);
  }
  
  ctx.lineWidth = 3;
  ctx.shadowBlur = 12;
  
  if (isStreaming) {
    ctx.strokeStyle = '#e11d48'; // Active Recording Red
    ctx.shadowColor = 'rgba(225, 29, 72, 0.6)';
  } else {
    ctx.strokeStyle = isConnected ? '#0891b2' : '#4b5563'; // Quiet Cyan or Idle Grey
    ctx.shadowColor = isConnected ? 'rgba(8, 145, 178, 0.4)' : 'rgba(75, 85, 99, 0.2)';
  }
  
  ctx.beginPath();
  
  if (bufferLength === 0 || !dataArray) {
    // Draw steady, subtle idle sine wave representation or simple flat center line
    ctx.moveTo(0, height / 2);
    
    // Let's draw a tiny idle wave if connected to look active and responsive
    if (isConnected) {
      const time = Date.now() * 0.004;
      for (let x = 0; x < width; x++) {
        const y = height / 2 + Math.sin(x * 0.02 + time) * 2;
        ctx.lineTo(x, y);
      }
    } else {
      ctx.lineTo(width, height / 2);
    }
  } else {
    // Draw active audio signal wave
    const sliceWidth = width / bufferLength;
    let x = 0;
    
    for (let i = 0; i < bufferLength; i++) {
      const v = dataArray[i] / 128.0; // Normalized representation around 1.0
      const y = (v * height) / 2;
      
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
      
      x += sliceWidth;
    }
  }
  
  ctx.stroke();
  ctx.shadowBlur = 0; // Reset canvas shadow context
}

// --- Event Bindings ---
function setupEventListeners() {
  // Connection management
  connectBtn.addEventListener('click', () => {
    if (isConnected) {
      disconnectServer();
    } else {
      connectServer();
    }
  });
  
  // Settings Panel drawer toggling
  settingsToggleBtn.addEventListener('click', openDrawer);
  settingsCloseBtn.addEventListener('click', closeDrawer);
  drawerOverlay.addEventListener('click', closeDrawer);
  saveSettingsBtn.addEventListener('click', saveSettings);
  
  // Mode configuration selectors
  document.getElementById('mode-ptt').addEventListener('click', () => setMode('ptt'));
  document.getElementById('mode-stream').addEventListener('click', () => setMode('stream'));
  
  // Push-To-Talk interactive handlers
  
  // Desktop mouse handlers
  pttBtn.addEventListener('mousedown', () => {
    if (mode === 'ptt') startVoiceStream();
  });
  
  const handleMouseRelease = () => {
    if (mode === 'ptt') stopVoiceStream();
  };
  pttBtn.addEventListener('mouseup', handleMouseRelease);
  pttBtn.addEventListener('mouseleave', handleMouseRelease);
  
  // Touch screen mobile handlers
  pttBtn.addEventListener('touchstart', (e) => {
    e.preventDefault();
    if (mode === 'ptt') startVoiceStream();
  }, { passive: false });
  
  const handleTouchRelease = (e) => {
    e.preventDefault();
    if (mode === 'ptt') stopVoiceStream();
  };
  pttBtn.addEventListener('touchend', handleTouchRelease, { passive: false });
  pttBtn.addEventListener('touchcancel', handleTouchRelease, { passive: false });
  
  // Continuous Toggle click handler
  pttBtn.addEventListener('click', () => {
    if (mode === 'stream') {
      if (isStreaming) {
        stopVoiceStream();
      } else {
        startVoiceStream();
      }
    }
  });
}

// --- Entrypoint ---
window.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  setupEventListeners();
  
  // Start the canvas render loop
  renderVisualizer();
});
