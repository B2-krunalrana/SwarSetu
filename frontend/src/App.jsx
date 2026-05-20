import React, { useState, useEffect, useRef } from 'react';

// --- Inline AudioWorklet Code (captures raw float samples at native hardware rate) ---
const WORKLET_CODE = `
class AudioProcessor extends AudioWorkletProcessor {
  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (input && input[0]) {
      this.port.postMessage(input[0]);
    }
    return true;
  }
}
registerProcessor('swarsetu-audio-processor', AudioProcessor);
`;

// --- Helper: Float32Array → Int16 little-endian PCM ArrayBuffer ---
function floatTo16BitPCM(float32Array) {
  const buffer = new ArrayBuffer(float32Array.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1.0, Math.min(1.0, float32Array[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }
  return buffer;
}

// --- Helper: decode an audio File into Float32 PCM at a target sample rate ---
async function decodeAudioFile(file, targetSampleRate) {
  const arrayBuffer = await file.arrayBuffer();
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  const offlineCtx = new OfflineAudioContext(1, 1, targetSampleRate);
  const decoded = await offlineCtx.decodeAudioData(arrayBuffer);

  // Resample to targetSampleRate using OfflineAudioContext
  const offlineCtx2 = new OfflineAudioContext(
    1,
    Math.ceil(decoded.duration * targetSampleRate),
    targetSampleRate
  );
  const source = offlineCtx2.createBufferSource();
  source.buffer = decoded;
  source.connect(offlineCtx2.destination);
  source.start(0);
  const rendered = await offlineCtx2.startRendering();
  return rendered.getChannelData(0); // Float32Array at targetSampleRate
}

export default function App() {
  // ── Connection state ──
  const [wsUrl, setWsUrl]           = useState('');
  const [sampleRate, setSampleRate] = useState(44100);
  const [chunkSize, setChunkSize]   = useState(4096);
  const [connState, setConnState]   = useState('disconnected');
  const [errorMsg, setErrorMsg]     = useState(null);

  // ── Broadcast mode: 'ptt' | 'continuous' | 'record' | 'file' ──
  const [mode, setMode] = useState('ptt');

  // ── Live streaming states ──
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const [isPTTPressed,   setIsPTTPressed]   = useState(false);
  const [packetsSent,    setPacketsSent]    = useState(0);
  const [actualRate,     setActualRate]     = useState(null); // real hardware rate

  // ── Record-then-play states ──
  const [isRecording,   setIsRecording]   = useState(false);
  const [recordedBlob,  setRecordedBlob]  = useState(null);
  const [recDuration,   setRecDuration]   = useState(0);
  const [isSendingRec,  setIsSendingRec]  = useState(false);

  // ── File upload states ──
  const [uploadFile,    setUploadFile]    = useState(null);
  const [isSendingFile, setIsSendingFile] = useState(false);
  const [uploadProgress,setUploadProgress]= useState(0);

  // ── PWA install prompt ──
  const [pwaPrompt, setPwaPrompt] = useState(null);

  // ── Refs (non-reactive, used inside callbacks) ──
  const wsRef             = useRef(null);
  const audioCtxRef       = useRef(null);
  const micStreamRef      = useRef(null);
  const workletNodeRef    = useRef(null);
  const analyserRef       = useRef(null);
  const accRef            = useRef([]);
  const canvasRef         = useRef(null);
  const animFrameRef      = useRef(null);
  const mediaRecorderRef  = useRef(null);
  const recChunksRef      = useRef([]);
  const recTimerRef       = useRef(null);
  const chunkSizeRef      = useRef(chunkSize);
  const wsReadyRef        = useRef(false);

  // Keep chunkSizeRef in sync (used inside live worklet callback)
  useEffect(() => { chunkSizeRef.current = chunkSize; }, [chunkSize]);

  // ── Init defaults from localStorage ──
  useEffect(() => {
    const isHttps    = window.location.protocol === 'https:';
    const portSuffix = window.location.port ? `:${window.location.port}` : '';
    const defUrl = isHttps
      ? `wss://${window.location.hostname}${portSuffix}/ws/stream`
      : `ws://${window.location.hostname || 'localhost'}:8000/ws/stream`;

    setWsUrl(      localStorage.getItem('ss_url')         || defUrl);
    setSampleRate(+localStorage.getItem('ss_rate')        || 44100);
    setChunkSize( +localStorage.getItem('ss_chunk')       || 4096);

    const onInstall = (e) => { e.preventDefault(); setPwaPrompt(e); };
    window.addEventListener('beforeinstallprompt', onInstall);
    return () => {
      window.removeEventListener('beforeinstallprompt', onInstall);
      _disconnectAll();
    };
  }, []);

  const installPWA = () => {
    if (!pwaPrompt) return;
    pwaPrompt.prompt();
    pwaPrompt.userChoice.then(() => setPwaPrompt(null));
  };

  // ══════════════════════════════════════════════
  //  WebSocket management
  // ══════════════════════════════════════════════
  const connectServer = (e) => {
    if (e) e.preventDefault();
    setErrorMsg(null);
    setConnState('connecting');
    localStorage.setItem('ss_url',   wsUrl);
    localStorage.setItem('ss_rate',  sampleRate.toString());
    localStorage.setItem('ss_chunk', chunkSize.toString());

    try {
      // We send the sample rate so the server opens its OutputStream at the right rate
      const url = new URL(wsUrl);
      url.searchParams.set('sampleRate', sampleRate.toString());
      const ws = new WebSocket(url.toString());
      ws.binaryType = 'arraybuffer';
      wsRef.current = ws;

      ws.onopen  = () => { setConnState('connected'); wsReadyRef.current = true; };
      ws.onclose = () => { setConnState('disconnected'); wsReadyRef.current = false; _stopLive(); };
      ws.onerror = () => {
        setErrorMsg('Cannot reach server. Is it running with SSL?');
        setConnState('disconnected');
        wsReadyRef.current = false;
      };
    } catch {
      setErrorMsg('Invalid WebSocket URL format.');
      setConnState('disconnected');
    }
  };

  const _disconnectAll = () => {
    wsRef.current?.close();
    _stopLive();
    _stopRecording();
    setConnState('disconnected');
    wsReadyRef.current = false;
  };

  const _sendPCM = (float32Array) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(floatTo16BitPCM(float32Array));
    setPacketsSent(p => p + 1);
  };

  // ══════════════════════════════════════════════
  //  Live microphone pipeline (PTT / Continuous)
  // ══════════════════════════════════════════════
  const _startLive = async () => {
    setErrorMsg(null);
    accRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
      micStreamRef.current = stream;

      // Use native hardware sample rate — DO NOT force a rate here;
      // forcing a non-native rate causes the browser to do bad resampling or emit wrong sample counts
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      const ctx = new AudioContextClass();          // ← native rate!
      const nativeRate = ctx.sampleRate;
      audioCtxRef.current = ctx;
      setActualRate(nativeRate);

      // Register worklet
      const blob = new Blob([WORKLET_CODE], { type: 'application/javascript' });
      const blobUrl = URL.createObjectURL(blob);
      await ctx.audioWorklet.addModule(blobUrl);
      URL.revokeObjectURL(blobUrl);

      const src      = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;

      const worklet = new AudioWorkletNode(ctx, 'swarsetu-audio-processor');
      workletNodeRef.current = worklet;

      src.connect(analyser);
      src.connect(worklet);

      worklet.port.onmessage = ({ data: floatData }) => {
        const acc = accRef.current;
        for (let i = 0; i < floatData.length; i++) acc.push(floatData[i]);
        const sz = chunkSizeRef.current;
        while (acc.length >= sz) {
          _sendPCM(new Float32Array(acc.splice(0, sz)));
        }
      };

      setIsBroadcasting(true);
      _startVisualizer();
    } catch (err) {
      console.error(err);
      setErrorMsg('Microphone access denied or device busy. Check browser permissions.');
      setIsBroadcasting(false);
      setIsPTTPressed(false);
    }
  };

  const _stopLive = () => {
    cancelAnimationFrame(animFrameRef.current);
    workletNodeRef.current?.disconnect();
    workletNodeRef.current = null;
    micStreamRef.current?.getTracks().forEach(t => t.stop());
    micStreamRef.current = null;
    if (audioCtxRef.current?.state !== 'closed') audioCtxRef.current?.close();
    audioCtxRef.current = null;
    analyserRef.current = null;
    setIsBroadcasting(false);
    setIsPTTPressed(false);
    _drawBlank();
  };

  // ── PTT handlers ──
  const onPTTDown = (e) => {
    e.preventDefault();
    if (connState !== 'connected' || isPTTPressed) return;
    setIsPTTPressed(true);
    _startLive();
  };
  const onPTTUp = (e) => {
    e.preventDefault();
    if (!isPTTPressed) return;
    setIsPTTPressed(false);
    _stopLive();
  };

  // ── Continuous toggle ──
  const toggleContinuous = () => {
    if (connState !== 'connected') return;
    isBroadcasting ? _stopLive() : _startLive();
  };

  // ══════════════════════════════════════════════
  //  Record → Play mode
  // ══════════════════════════════════════════════
  const startRecording = async () => {
    setErrorMsg(null);
    recChunksRef.current = [];
    setRecordedBlob(null);
    setRecDuration(0);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStreamRef.current = stream;
      const mr = new MediaRecorder(stream);
      mediaRecorderRef.current = mr;
      mr.ondataavailable = (e) => { if (e.data.size > 0) recChunksRef.current.push(e.data); };
      mr.onstop = () => {
        const blob = new Blob(recChunksRef.current, { type: 'audio/webm' });
        setRecordedBlob(blob);
        stream.getTracks().forEach(t => t.stop());
        micStreamRef.current = null;
      };
      mr.start(100);
      setIsRecording(true);
      let secs = 0;
      recTimerRef.current = setInterval(() => { secs++; setRecDuration(secs); }, 1000);
    } catch {
      setErrorMsg('Microphone access denied.');
    }
  };

  const stopRecording = () => {
    clearInterval(recTimerRef.current);
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  const _stopRecording = () => {
    clearInterval(recTimerRef.current);
    if (mediaRecorderRef.current?.state !== 'inactive') mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  const sendRecording = async () => {
    if (!recordedBlob || connState !== 'connected') return;
    setIsSendingRec(true);
    setErrorMsg(null);
    try {
      // Decode webm → Float32 PCM at chosen sample rate
      const pcmFloat = await decodeAudioFile(recordedBlob, sampleRate);
      let offset = 0;
      const sz = chunkSize;
      while (offset < pcmFloat.length) {
        const slice = pcmFloat.slice(offset, offset + sz);
        _sendPCM(slice);
        offset += sz;
        // Small yield to avoid flooding
        await new Promise(r => setTimeout(r, (sz / sampleRate) * 1000 * 0.8));
      }
    } catch (err) {
      setErrorMsg('Failed to decode/send recording: ' + err.message);
    }
    setIsSendingRec(false);
  };

  const discardRecording = () => {
    setRecordedBlob(null);
    setRecDuration(0);
  };

  // ══════════════════════════════════════════════
  //  File upload → Play mode
  // ══════════════════════════════════════════════
  const onFileChange = (e) => {
    const f = e.target.files?.[0];
    if (f) { setUploadFile(f); setUploadProgress(0); }
  };

  const sendFile = async () => {
    if (!uploadFile || connState !== 'connected') return;
    setIsSendingFile(true);
    setErrorMsg(null);
    setUploadProgress(0);
    try {
      const pcmFloat = await decodeAudioFile(uploadFile, sampleRate);
      const totalChunks = Math.ceil(pcmFloat.length / chunkSize);
      let offset = 0;
      let sent = 0;
      while (offset < pcmFloat.length) {
        const slice = pcmFloat.slice(offset, offset + chunkSize);
        _sendPCM(slice);
        offset += chunkSize;
        sent++;
        setUploadProgress(Math.round((sent / totalChunks) * 100));
        await new Promise(r => setTimeout(r, (chunkSize / sampleRate) * 1000 * 0.8));
      }
      setUploadProgress(100);
    } catch (err) {
      setErrorMsg('Failed to decode/send file: ' + err.message);
    }
    setIsSendingFile(false);
  };

  // ══════════════════════════════════════════════
  //  Visualizer
  // ══════════════════════════════════════════════
  const _startVisualizer = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx2d   = canvas.getContext('2d');
    const analyser = analyserRef.current;
    if (!analyser) return;
    const buf = new Uint8Array(analyser.frequencyBinCount);
    const draw = () => {
      animFrameRef.current = requestAnimationFrame(draw);
      analyser.getByteTimeDomainData(buf);
      ctx2d.fillStyle = 'rgba(3,7,18,0.4)';
      ctx2d.fillRect(0, 0, canvas.width, canvas.height);
      ctx2d.lineWidth = 3;
      ctx2d.strokeStyle = '#ef4444';
      ctx2d.shadowBlur = 10;
      ctx2d.shadowColor = 'rgba(239,68,68,0.5)';
      ctx2d.beginPath();
      const sw = canvas.width / buf.length;
      let x = 0;
      for (let i = 0; i < buf.length; i++) {
        const y = (buf[i] / 128.0) * (canvas.height / 2);
        i === 0 ? ctx2d.moveTo(x, y) : ctx2d.lineTo(x, y);
        x += sw;
      }
      ctx2d.lineTo(canvas.width, canvas.height / 2);
      ctx2d.stroke();
      ctx2d.shadowBlur = 0;
    };
    draw();
  };

  const _drawBlank = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx2d = canvas.getContext('2d');
    ctx2d.fillStyle = '#030712';
    ctx2d.fillRect(0, 0, canvas.width, canvas.height);
    ctx2d.lineWidth = 2;
    ctx2d.strokeStyle = '#374151';
    ctx2d.beginPath();
    ctx2d.moveTo(0, canvas.height / 2);
    ctx2d.lineTo(canvas.width, canvas.height / 2);
    ctx2d.stroke();
  };

  useEffect(() => { _drawBlank(); }, [connState]);

  // ══════════════════════════════════════════════
  //  Helpers
  // ══════════════════════════════════════════════
  const fmtDuration = (s) => `${Math.floor(s/60).toString().padStart(2,'0')}:${(s%60).toString().padStart(2,'0')}`;

  // ══════════════════════════════════════════════
  //  Render
  // ══════════════════════════════════════════════
  return (
    <div className="app-container">

      {/* PWA Install Banner */}
      {pwaPrompt && (
        <div className="pwa-banner">
          <div className="pwa-info">
            <span className="pwa-title">📲 Install SwarSetu</span>
            <span className="pwa-desc">Add to home screen for quick access</span>
          </div>
          <button className="pwa-install-btn" onClick={installPWA}>Install</button>
        </div>
      )}

      <div className="glass-panel">

        {/* Header */}
        <header className="app-header">
          <div className="brand">
            <h1>SwarSetu</h1>
            <span>Voice Bridge</span>
          </div>
          <div className="status-badge">
            <span className={`status-dot ${connState}`}></span>
            <span style={{ textTransform: 'capitalize' }}>{connState}</span>
          </div>
        </header>

        {/* Error Box */}
        {errorMsg && (
          <div className="error-box">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <span>{errorMsg}</span>
          </div>
        )}

        {/* ═══════════ VIEW 1: DISCONNECTED ═══════════ */}
        {connState !== 'connected' && (
          <form onSubmit={connectServer}>
            <div className="form-group">
              <label>Server WebSocket URL</label>
              <input type="text" className="input-field" value={wsUrl}
                onChange={e => setWsUrl(e.target.value)}
                placeholder="wss://<IP>:8000/ws/stream" required />
            </div>

            <div className="form-group">
              <label>Sample Rate</label>
              <select className="input-field select-field" value={sampleRate}
                onChange={e => setSampleRate(+e.target.value)}>
                <option value={44100}>44.1 kHz — Best Quality</option>
                <option value={22050}>22 kHz — Good Balance</option>
                <option value={16000}>16 kHz — Walkie-Talkie</option>
                <option value={8000}>8 kHz — Ultra Low Bandwidth</option>
              </select>
            </div>

            <div className="form-group">
              <label>Buffer Block Size</label>
              <select className="input-field select-field" value={chunkSize}
                onChange={e => setChunkSize(+e.target.value)}>
                <option value={4096}>4096 — Smooth / Stable</option>
                <option value={2048}>2048 — Balanced</option>
                <option value={1024}>1024 — Lower Latency</option>
                <option value={512}>512 — Ultra Low Latency</option>
              </select>
            </div>

            <button type="submit" className="action-btn" disabled={connState === 'connecting'}>
              {connState === 'connecting' ? 'Connecting...' : (
                <><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M5 12h14M12 5l7 7-7 7"/></svg> Connect Server</>
              )}
            </button>
            <p className="info-tip">Use HTTPS with SSL certs for microphone access on mobile.</p>
          </form>
        )}

        {/* ═══════════ VIEW 2: CONNECTED ═══════════ */}
        {connState === 'connected' && (
          <div className="ptt-screen-container">

            {/* Visualizer (shown for live modes only) */}
            {(mode === 'ptt' || mode === 'continuous') && (
              <div className="visualizer-container">
                <canvas ref={canvasRef} width="350" height="80" className="visualizer-canvas" />
              </div>
            )}

            {/* Mode Tabs — 4 modes */}
            <div className="mode-container">
              {['ptt', 'continuous', 'record', 'file'].map(m => (
                <button key={m}
                  className={`mode-tab ${mode === m ? 'active' : ''}`}
                  onClick={() => { _stopLive(); _stopRecording(); setMode(m); }}>
                  {m === 'ptt' ? 'PTT' : m === 'continuous' ? 'Live' : m === 'record' ? 'Record' : 'File'}
                </button>
              ))}
            </div>

            {/* ── PTT mode ── */}
            {mode === 'ptt' && (
              <div className={`ptt-button-outer ${isPTTPressed ? 'active' : 'idle'}`}
                onMouseDown={onPTTDown} onMouseUp={onPTTUp} onMouseLeave={onPTTUp}
                onTouchStart={onPTTDown} onTouchEnd={onPTTUp}>
                <div className="ptt-button-inner">
                  <svg className="ptt-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={isPTTPressed ? 2.5 : 2}>
                    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                    <line x1="12" y1="19" x2="12" y2="22"/>
                  </svg>
                  <span className="ptt-label" style={{ color: isPTTPressed ? '#ef4444' : undefined }}>
                    {isPTTPressed ? 'TALKING...' : 'HOLD TO TALK'}
                  </span>
                </div>
              </div>
            )}

            {/* ── Continuous Live mode ── */}
            {mode === 'continuous' && (
              <div className={`ptt-button-outer ${isBroadcasting ? 'active' : 'idle'}`} onClick={toggleContinuous}>
                <div className="ptt-button-inner">
                  <svg className="ptt-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
                    style={isBroadcasting ? { animation: 'blink 1.5s infinite' } : {}}>
                    <circle cx="12" cy="12" r="2"/>
                    <path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/>
                  </svg>
                  <span className="ptt-label" style={{ color: isBroadcasting ? '#ef4444' : undefined }}>
                    {isBroadcasting ? 'ON AIR' : 'TAP TO START'}
                  </span>
                </div>
              </div>
            )}

            {/* ── Record then Play mode ── */}
            {mode === 'record' && (
              <div className="record-panel">
                {!recordedBlob ? (
                  // Recording controls
                  <div className="rec-controls">
                    {isRecording && (
                      <div className="rec-status">
                        <span className="rec-dot"></span>
                        <span className="rec-time">{fmtDuration(recDuration)}</span>
                        <span style={{ color: '#ef4444', fontSize: '0.8rem', fontWeight: 700 }}>REC</span>
                      </div>
                    )}
                    <div className={`ptt-button-outer ${isRecording ? 'active' : 'idle'}`}
                      onClick={isRecording ? stopRecording : startRecording}>
                      <div className="ptt-button-inner">
                        <svg className="ptt-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          {isRecording
                            ? <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" stroke="none"/>
                            : <><circle cx="12" cy="12" r="6" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="10"/></>}
                        </svg>
                        <span className="ptt-label" style={{ color: isRecording ? '#ef4444' : undefined }}>
                          {isRecording ? 'STOP REC' : 'START REC'}
                        </span>
                      </div>
                    </div>
                    <p className="info-tip">Record your voice. Then review and send it to the speaker.</p>
                  </div>
                ) : (
                  // Playback / send controls
                  <div className="rec-ready">
                    <div className="rec-preview">
                      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" strokeWidth="2">
                        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                        <line x1="12" y1="19" x2="12" y2="22"/>
                      </svg>
                      <div>
                        <span className="rec-ready-label">Recording Ready</span>
                        <span className="rec-ready-dur">{fmtDuration(recDuration)}</span>
                      </div>
                    </div>
                    <audio controls src={URL.createObjectURL(recordedBlob)} className="audio-preview" />
                    <button className="action-btn" onClick={sendRecording} disabled={isSendingRec}>
                      {isSendingRec ? 'Sending to Speakers...' : (
                        <><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <polygon points="5 3 19 12 5 21 5 3"/>
                        </svg> Play on Laptop Speakers</>
                      )}
                    </button>
                    <button className="disconnect-btn" onClick={discardRecording} style={{ marginTop: '0.5rem' }}>
                      🗑 Discard Recording
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* ── File Upload mode ── */}
            {mode === 'file' && (
              <div className="record-panel">
                <div className="file-upload-zone" onClick={() => document.getElementById('audio-file-input').click()}>
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" strokeWidth="1.5">
                    <path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>
                  </svg>
                  <span>{uploadFile ? uploadFile.name : 'Tap to select MP3 / WAV / OGG'}</span>
                  {uploadFile && <span className="file-size">{(uploadFile.size / 1024).toFixed(1)} KB</span>}
                </div>
                <input id="audio-file-input" type="file" accept="audio/*" style={{ display: 'none' }} onChange={onFileChange} />

                {uploadFile && (
                  <>
                    {isSendingFile && (
                      <div className="upload-progress-wrap">
                        <div className="upload-progress-bar" style={{ width: `${uploadProgress}%` }}></div>
                        <span className="upload-progress-label">{uploadProgress}%</span>
                      </div>
                    )}
                    <button className="action-btn" onClick={sendFile} disabled={isSendingFile}>
                      {isSendingFile ? `Streaming… ${uploadProgress}%` : (
                        <><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <polygon points="5 3 19 12 5 21 5 3"/>
                        </svg> Play File on Laptop Speakers</>
                      )}
                    </button>
                    {!isSendingFile && (
                      <button className="disconnect-btn" style={{ marginTop: '0.5rem' }}
                        onClick={() => { setUploadFile(null); setUploadProgress(0); }}>
                        🗑 Remove File
                      </button>
                    )}
                  </>
                )}
                <p className="info-tip">Audio is decoded in browser to PCM and streamed to your laptop's speakers.</p>
              </div>
            )}

            {/* Stats (live modes only) */}
            {(mode === 'ptt' || mode === 'continuous') && (
              <div className="stats-grid">
                <div className="stat-item"><span>Sample Rate</span>
                  <span className="stat-val">{actualRate ? `${(actualRate/1000).toFixed(1)} kHz` : `${sampleRate/1000} kHz`}</span>
                </div>
                <div className="stat-item"><span>Block Size</span>
                  <span className="stat-val">{chunkSize} smp</span>
                </div>
                <div className="stat-item"><span>Packets Sent</span>
                  <span className="stat-val">{packetsSent}</span>
                </div>
                <div className="stat-item"><span>Est. Bitrate</span>
                  <span className="stat-val">
                    {isBroadcasting && actualRate ? `${((actualRate * 16) / 1024).toFixed(0)} kbps` : '—'}
                  </span>
                </div>
              </div>
            )}

            <button className="disconnect-btn" onClick={_disconnectAll} style={{ marginTop: '1.5rem' }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
              Disconnect Bridge
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
