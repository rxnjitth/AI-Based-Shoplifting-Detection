/**
 * Live Detection Component
 * Real-time object detection from camera feed.
 */
import React, { useState, useRef, useEffect } from 'react';
import { liveApi } from '../services/api';

interface Detection {
  person: {
    bbox: number[];
    confidence: number;
  };
  pose: {
    detected: boolean;
    landmarks_count: number;
  };
  interaction: {
    zone: string;
    left_hand_action: string;
    right_hand_action: string;
    nearby_products: number;
  };
  suspicious: boolean;
}

interface DetectionResult {
  success: boolean;
  detections: Detection[];
  person_count: number;
  product_count: number;
  has_suspicious_activity: boolean;
}

const LiveDetection: React.FC = () => {
  const [cameras, setCameras] = useState<MediaDeviceInfo[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<string>('');
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isActive, setIsActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detectionResult, setDetectionResult] = useState<DetectionResult | null>(null);
  const [fps, setFps] = useState<number>(0);
  const [processing, setProcessing] = useState(false);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const lastFrameTime = useRef<number>(0);
  const frameCount = useRef<number>(0);
  const fpsInterval = useRef<number>(1000); // Update FPS every second

  // Enumerate cameras
  const enumerateCameras = async () => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(device => device.kind === 'videoinput');
      setCameras(videoDevices);
      
      if (videoDevices.length > 0 && !selectedCamera) {
        setSelectedCamera(videoDevices[0].deviceId);
      }
    } catch (err) {
      setError('Failed to enumerate cameras. Please check permissions.');
    }
  };

  // Start camera
  const startCamera = async () => {
    try {
      setError(null);
      console.log('Starting camera with deviceId:', selectedCamera);
      
      const constraints: MediaStreamConstraints = {
        video: selectedCamera ? { 
          deviceId: { exact: selectedCamera },
          width: { ideal: 1280 },
          height: { ideal: 720 }
        } : true,
        audio: false
      };
      
      console.log('Requesting camera access with constraints:', constraints);
      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      console.log('Camera stream obtained:', mediaStream);
      
      setStream(mediaStream);
      setIsActive(true);
    } catch (err: any) {
      console.error('Camera error:', err);
      setError(`Camera access failed: ${err.message || 'Unknown error'}`);
    }
  };

  // Stop camera
  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    setIsActive(false);
    if (animationRef.current) {
      clearTimeout(animationRef.current);
    }
  };

  // Update video element when stream changes
  useEffect(() => {
    if (videoRef.current && stream) {
      console.log('Attaching stream to video element');
      videoRef.current.srcObject = stream;
      videoRef.current.play().catch(e => console.error('Video play error:', e));
    }
  }, [stream]);

  // Cleanup on unmount
  useEffect(() => {
    enumerateCameras();
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
      if (animationRef.current) {
        clearTimeout(animationRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Capture frame and send for detection
  const captureAndDetect = async () => {
    if (!videoRef.current || !canvasRef.current || processing) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    if (!ctx || video.readyState !== video.HAVE_ENOUGH_DATA) return;

    // Set canvas size to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Draw current frame
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert to base64
    const imageData = canvas.toDataURL('image/jpeg', 0.8);

    try {
      setProcessing(true);
      const result = await liveApi.detectFrame(imageData);
      setDetectionResult(result);
      
      // Draw bounding boxes
      drawDetections(ctx, result.detections, canvas.width, canvas.height);
      
      // Update FPS
      frameCount.current++;
      const now = Date.now();
      if (now - lastFrameTime.current >= fpsInterval.current) {
        setFps(frameCount.current);
        frameCount.current = 0;
        lastFrameTime.current = now;
      }
    } catch (err: any) {
      console.error('Detection failed:', err);
      const errorMsg = err?.response?.data?.detail || err?.message || 'Unknown error';
      setError(`Detection error: ${errorMsg}`);
    } finally {
      setProcessing(false);
    }
  };

  // Draw detection results on canvas
  const drawDetections = (
    ctx: CanvasRenderingContext2D,
    detections: Detection[],
    width: number,
    height: number
  ) => {
    detections.forEach((detection) => {
      const bbox = detection.person.bbox;
      const [x1, y1, x2, y2] = bbox;
      
      // Determine box color based on suspicion
      const color = detection.suspicious ? '#ef4444' : '#10b981';
      
      // Draw bounding box
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
      
      // Draw label background
      const label = `${detection.interaction.zone} - ${detection.interaction.left_hand_action}`;
      const labelWidth = ctx.measureText(label).width + 10;
      
      ctx.fillStyle = color;
      ctx.fillRect(x1, y1 - 25, labelWidth, 25);
      
      // Draw label text
      ctx.fillStyle = '#ffffff';
      ctx.font = '14px Arial';
      ctx.fillText(label, x1 + 5, y1 - 8);
      
      // Draw suspicious indicator
      if (detection.suspicious) {
        ctx.fillStyle = '#ef4444';
        ctx.font = 'bold 16px Arial';
        ctx.fillText('⚠ SUSPICIOUS', x1, y1 + 20);
      }
    });
  };

  // Detection loop
  useEffect(() => {
    if (!isActive) return;

    const detectLoop = () => {
      captureAndDetect();
      // Detect every 500ms (2 FPS) to avoid overwhelming the backend
      animationRef.current = window.setTimeout(() => {
        requestAnimationFrame(detectLoop);
      }, 500);
    };

    detectLoop();

    return () => {
      if (animationRef.current) {
        clearTimeout(animationRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isActive]);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-gray-900">Live Object Detection</h2>
        <div className="text-sm text-gray-600">
          FPS: {fps} | Processing: {processing ? '🔄' : '✓'}
        </div>
      </div>

      {/* Camera Selection */}
      <div className="mb-4 flex gap-4">
        <select
          value={selectedCamera}
          onChange={(e) => setSelectedCamera(e.target.value)}
          disabled={isActive}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="">Select Camera</option>
          {cameras.map((camera) => (
            <option key={camera.deviceId} value={camera.deviceId}>
              {camera.label || `Camera ${camera.deviceId.substring(0, 8)}`}
            </option>
          ))}
        </select>

        <button
          onClick={isActive ? stopCamera : startCamera}
          className={`px-6 py-2 rounded-md font-semibold transition-colors ${
            isActive
              ? 'bg-red-600 hover:bg-red-700 text-white'
              : 'bg-primary-600 hover:bg-primary-700 text-white'
          }`}
        >
          {isActive ? '⏹ Stop' : '▶ Start'} Detection
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      {/* Video Display */}
      <div className="relative bg-black rounded-lg overflow-hidden" style={{ aspectRatio: '16/9' }}>
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-contain"
          style={{ display: isActive ? 'block' : 'none' }}
        />
        <canvas
          ref={canvasRef}
          className="absolute top-0 left-0 w-full h-full object-contain"
        />
        {!isActive && (
          <div className="absolute inset-0 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <svg className="mx-auto h-16 w-16 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              <p>Click "Start Detection" to begin</p>
            </div>
          </div>
        )}
      </div>

      {/* Detection Stats */}
      {detectionResult && isActive && (
        <div className="mt-4 grid grid-cols-4 gap-4">
          <div className="bg-blue-50 p-3 rounded-lg">
            <div className="text-sm text-gray-600">Persons</div>
            <div className="text-2xl font-bold text-blue-600">{detectionResult.person_count}</div>
          </div>
          <div className="bg-green-50 p-3 rounded-lg">
            <div className="text-sm text-gray-600">Products</div>
            <div className="text-2xl font-bold text-green-600">{detectionResult.product_count}</div>
          </div>
          <div className="bg-purple-50 p-3 rounded-lg">
            <div className="text-sm text-gray-600">Detections</div>
            <div className="text-2xl font-bold text-purple-600">{detectionResult.detections.length}</div>
          </div>
          <div className={`p-3 rounded-lg ${detectionResult.has_suspicious_activity ? 'bg-red-50' : 'bg-gray-50'}`}>
            <div className="text-sm text-gray-600">Status</div>
            <div className={`text-2xl font-bold ${detectionResult.has_suspicious_activity ? 'text-red-600' : 'text-gray-600'}`}>
              {detectionResult.has_suspicious_activity ? '⚠ Alert' : '✓ Clear'}
            </div>
          </div>
        </div>
      )}

      {/* Detection Details */}
      {detectionResult && detectionResult.detections.length > 0 && (
        <div className="mt-4">
          <h3 className="font-semibold mb-2">Detection Details</h3>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {detectionResult.detections.map((det, idx) => (
              <div
                key={idx}
                className={`p-3 rounded border ${
                  det.suspicious ? 'bg-red-50 border-red-300' : 'bg-gray-50 border-gray-300'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-semibold">
                      Person #{idx + 1} {det.suspicious && <span className="text-red-600">⚠ SUSPICIOUS</span>}
                    </div>
                    <div className="text-sm text-gray-600">
                      Zone: <span className="font-medium">{det.interaction.zone}</span>
                    </div>
                    <div className="text-sm text-gray-600">
                      Left: {det.interaction.left_hand_action} | Right: {det.interaction.right_hand_action}
                    </div>
                    {det.interaction.nearby_products > 0 && (
                      <div className="text-sm text-orange-600">
                        📦 {det.interaction.nearby_products} nearby products
                      </div>
                    )}
                  </div>
                  <div className="text-sm text-gray-500">
                    {Math.round(det.person.confidence * 100)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default LiveDetection;
