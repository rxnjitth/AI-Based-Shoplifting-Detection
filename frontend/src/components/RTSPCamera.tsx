/**
 * RTSPCamera Component
 * Connect to an EZVIZ (or any RTSP) camera directly from the backend.
 * The backend pulls frames — no browser camera permission needed.
 */
import React, { useState, useEffect, useRef } from 'react';
import { rtspApi } from '../services/api';

interface CameraStatus {
  camera_id: string;
  status: string;
  error: string | null;
  frames_processed: number;
  alerts_generated: number;
  fps: number;
  uptime_seconds: number;
}

const RTSPCamera: React.FC = () => {
  const [cameraId, setCameraId] = useState('ezviz-1');
  const [rtspUrl, setRtspUrl] = useState('');
  const [useManualUrl, setUseManualUrl] = useState(true);
  const [ip, setIp] = useState('');
  const [port, setPort] = useState('554');
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [stream, setStream] = useState<'main' | 'sub'>('main');

  const [status, setStatus] = useState<CameraStatus | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewTs, setPreviewTs] = useState<number>(Date.now());

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const previewRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isRunning = status?.status === 'running';

  // Auto-load default camera config from backend (.env)
  useEffect(() => {
    rtspApi.getDefaultCamera()
      .then(cfg => {
        if (cfg.camera_id) setCameraId(cfg.camera_id);
        if (cfg.rtsp_url) { setRtspUrl(cfg.rtsp_url); setUseManualUrl(true); }
        if (cfg.port)   setPort(String(cfg.port));
        if (cfg.stream) setStream(cfg.stream as 'main' | 'sub');
      })
      .catch(() => {/* no defaults configured */});
  }, []);

  // Poll status + refresh preview while running
  useEffect(() => {
    if (!isRunning) return;

    pollRef.current = setInterval(async () => {
      try {
        const s = await rtspApi.getStatus(cameraId);
        setStatus(s);
      } catch { /* stream may have stopped */ }
    }, 2000);

    previewRef.current = setInterval(() => setPreviewTs(Date.now()), 1000);

    return () => {
      if (pollRef.current)  clearInterval(pollRef.current);
      if (previewRef.current) clearInterval(previewRef.current);
    };
  }, [isRunning, cameraId]);

  const handleConnect = async () => {
    setError(null);
    setConnecting(true);
    try {
      const payload: any = { camera_id: cameraId, stream };
      if (useManualUrl) {
        payload.rtsp_url = rtspUrl;
      } else {
        payload.rtsp_url = '';
        payload.ip       = ip;
        payload.port     = parseInt(port, 10);
        payload.username = username;
        payload.password = password;
      }
      const res = await rtspApi.connect(payload);
      setStatus({
        camera_id: cameraId,
        status: res.status,
        error: null,
        frames_processed: 0,
        alerts_generated: 0,
        fps: 0,
        uptime_seconds: 0,
      });
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Connection failed');
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await rtspApi.disconnect(cameraId);
      setStatus(null);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Disconnect failed');
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">📷 EZVIZ / RTSP Camera</h2>

      {/* Connection form — hidden while stream is running */}
      {!isRunning && (
        <div className="space-y-4 mb-6">

          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-gray-700 w-28">Camera ID</label>
            <input
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              value={cameraId}
              onChange={e => setCameraId(e.target.value)}
              placeholder="e.g. entrance"
            />
          </div>

          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-gray-700 w-28">Stream</label>
            <select
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              value={stream}
              onChange={e => setStream(e.target.value as 'main' | 'sub')}
            >
              <option value="main">Main (1080p)</option>
              <option value="sub">Sub (480p — lower CPU)</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="manualUrl"
              checked={useManualUrl}
              onChange={e => setUseManualUrl(e.target.checked)}
              className="rounded"
            />
            <label htmlFor="manualUrl" className="text-sm text-gray-700">
              Use full RTSP URL
            </label>
          </div>

          {useManualUrl ? (
            <div className="flex items-center gap-3">
              <label className="text-sm font-medium text-gray-700 w-28">RTSP URL</label>
              <input
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={rtspUrl}
                onChange={e => setRtspUrl(e.target.value)}
                placeholder="rtsp://admin:password@192.168.1.100:554/ch1/main"
              />
            </div>
          ) : (
            <>
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-gray-700 w-28">Camera IP</label>
                <input
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={ip}
                  onChange={e => setIp(e.target.value)}
                  placeholder="10.135.113.177"
                />
              </div>
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-gray-700 w-28">Port</label>
                <input
                  className="w-24 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={port}
                  onChange={e => setPort(e.target.value)}
                />
              </div>
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-gray-700 w-28">Username</label>
                <input
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                />
              </div>
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-gray-700 w-28">Password</label>
                <input
                  type="password"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                />
              </div>
            </>
          )}

          <button
            onClick={handleConnect}
            disabled={connecting}
            className="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-md font-semibold transition-colors disabled:opacity-50"
          >
            {connecting ? '⏳ Connecting...' : '▶ Connect Camera'}
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded text-sm">
          {error}
        </div>
      )}

      {/* Live preview + stats */}
      {isRunning && status && (
        <div>
          <div className="relative bg-black rounded-lg overflow-hidden mb-4" style={{ aspectRatio: '16/9' }}>
            <img
              src={`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/rtsp/preview/${cameraId}?t=${previewTs}`}
              alt="Live preview"
              className="w-full h-full object-contain"
              onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
            <div className="absolute top-2 left-2 bg-red-600 text-white text-xs font-bold px-2 py-1 rounded">
              ● LIVE
            </div>
          </div>

          <div className="grid grid-cols-4 gap-4 mb-4">
            <div className="bg-blue-50 p-3 rounded-lg">
              <div className="text-xs text-gray-500">Status</div>
              <div className="text-sm font-bold text-blue-600 capitalize">{status.status}</div>
            </div>
            <div className="bg-green-50 p-3 rounded-lg">
              <div className="text-xs text-gray-500">FPS</div>
              <div className="text-sm font-bold text-green-600">{status.fps}</div>
            </div>
            <div className="bg-purple-50 p-3 rounded-lg">
              <div className="text-xs text-gray-500">Frames</div>
              <div className="text-sm font-bold text-purple-600">{status.frames_processed.toLocaleString()}</div>
            </div>
            <div className="bg-red-50 p-3 rounded-lg">
              <div className="text-xs text-gray-500">Alerts</div>
              <div className="text-sm font-bold text-red-600">{status.alerts_generated}</div>
            </div>
          </div>

          {status.error && (
            <div className="mb-3 p-3 bg-red-100 border border-red-400 text-red-700 rounded text-sm">
              ⚠ Stream error: {status.error}
            </div>
          )}

          <div className="text-xs text-gray-500 mb-4">
            Uptime: {Math.floor(status.uptime_seconds / 60)}m {Math.floor(status.uptime_seconds % 60)}s
            &nbsp;·&nbsp; Camera: {cameraId}
          </div>

          <button
            onClick={handleDisconnect}
            className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md font-semibold transition-colors"
          >
            ⏹ Disconnect
          </button>
        </div>
      )}

      {!isRunning && (
        <p className="text-xs text-gray-400 mt-2">
          Detection runs on the backend — no browser camera permission needed.
        </p>
      )}
    </div>
  );
};

export default RTSPCamera;
