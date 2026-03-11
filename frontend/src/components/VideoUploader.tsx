/**
 * Video Uploader Component
 * Handles video file upload and live camera recording with progress tracking.
 */
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { videosApi } from '../services/api';

interface VideoUploaderProps {
  onUploadSuccess?: (jobId: string) => void;
}

type UploadMode = 'file' | 'camera';

const VideoUploader: React.FC<VideoUploaderProps> = ({ onUploadSuccess }) => {
  // Common state
  const [mode, setMode] = useState<UploadMode>('file');
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // File upload refs
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Camera state
  const [cameras, setCameras] = useState<MediaDeviceInfo[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<string>('');
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [recording, setRecording] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  // Stop camera on cleanup
  const stopCamera = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  }, [stream]);
  
  const enumerateCameras = useCallback(async () => {
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
  }, [selectedCamera]);
  
  const startCamera = async () => {
    try {
      setError(null);
      const constraints: MediaStreamConstraints = {
        video: selectedCamera ? { deviceId: { exact: selectedCamera } } : true,
        audio: false
      };
      
      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      setStream(mediaStream);
    } catch (err: any) {
      setError(`Camera access denied: ${err.message}`);
    }
  };
  
  const handleCameraChange = async (event: React.ChangeEvent<HTMLSelectElement>) => {
    const deviceId = event.target.value;
    setSelectedCamera(deviceId);
    
    if (stream) {
      stopCamera();
      // Small delay to ensure previous stream is stopped
      setTimeout(() => startCamera(), 100);
    }
  };
  
  // Enumerate cameras on mount
  useEffect(() => {
    if (mode === 'camera') {
      enumerateCameras();
    }
    
    return () => {
      stopCamera();
    };
  }, [mode, enumerateCameras, stopCamera]);
  
  // Update video element when stream changes
  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);
  
  const startRecording = () => {
    if (!stream) return;
    
    try {
      setError(null);
      
      const options: MediaRecorderOptions = {
        mimeType: 'video/webm;codecs=vp8',
      };
      
      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;
      
      const chunks: Blob[] = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        await handleRecordingComplete(chunks);
      };
      
      mediaRecorder.start(100); // Collect data every 100ms
      setRecording(true);
    } catch (err: any) {
      setError(`Recording failed: ${err.message}`);
    }
  };
  
  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setRecording(false);
    }
  };
  
  const handleRecordingComplete = async (chunks: Blob[]) => {
    if (chunks.length === 0) {
      setError('No recording data captured.');
      return;
    }
    
    const blob = new Blob(chunks, { type: 'video/webm' });
    const file = new File([blob], `camera-recording-${Date.now()}.webm`, { type: 'video/webm' });
    
    await uploadFile(file);
  };
  
  const uploadFile = async (file: File) => {
    // Validate file size (max 500MB)
    const maxSize = 500 * 1024 * 1024;
    if (file.size > maxSize) {
      setError('File too large. Maximum size is 500MB.');
      return;
    }

    try {
      setUploading(true);
      setError(null);
      setMessage(null);
      setProgress(0);

      const response = await videosApi.uploadVideo(file, (progress) => {
        setProgress(progress);
      });

      setMessage(`✅ ${response.message}`);
      setProgress(100);

      if (onUploadSuccess) {
        onUploadSuccess(response.job_id);
      }

      // Reset after 3 seconds
      setTimeout(() => {
        setMessage(null);
        setProgress(0);
      }, 3000);

    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['video/mp4', 'video/avi', 'video/mov', 'video/x-matroska'];
    if (!allowedTypes.includes(file.type) && !file.name.match(/\.(mp4|avi|mov|mkv)$/i)) {
      setError('Invalid file type. Please upload MP4, AVI, MOV, or MKV files.');
      return;
    }

    await uploadFile(file);
    
    // Reset file input
    setTimeout(() => {
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }, 3000);
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">Video Input for Analysis</h2>
      
      {/* Mode Toggle */}
      <div className="flex mb-6 border-b border-gray-200">
        <button
          onClick={() => {
            setMode('file');
            stopCamera();
          }}
          className={`flex-1 py-2 px-4 text-sm font-medium transition-colors ${
            mode === 'file'
              ? 'border-b-2 border-primary-600 text-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Upload File
        </button>
        <button
          onClick={() => setMode('camera')}
          className={`flex-1 py-2 px-4 text-sm font-medium transition-colors ${
            mode === 'camera'
              ? 'border-b-2 border-primary-600 text-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Live Camera
        </button>
      </div>

      {/* File Upload Mode */}
      {mode === 'file' && (
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-primary-500 transition-colors">
          <div className="mb-4">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              stroke="currentColor"
              fill="none"
              viewBox="0 0 48 48"
            >
              <path
                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>

          <label htmlFor="file-upload" className="cursor-pointer">
            <span className="mt-2 block text-sm font-medium text-gray-900">
              {uploading ? 'Uploading...' : 'Click to upload or drag and drop'}
            </span>
            <span className="mt-1 block text-xs text-gray-500">
              MP4, AVI, MOV, MKV up to 500MB
            </span>
            <input
              ref={fileInputRef}
              id="file-upload"
              name="file-upload"
              type="file"
              className="sr-only"
              accept="video/mp4,video/avi,video/mov,video/x-matroska,.mp4,.avi,.mov,.mkv"
              onChange={handleFileSelect}
              disabled={uploading}
            />
          </label>

          {uploading && (
            <div className="mt-4">
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div
                  className="bg-primary-600 h-2.5 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <p className="mt-2 text-sm text-gray-600">{progress}% uploaded</p>
            </div>
          )}

          {message && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
              <p className="text-sm text-green-800">{message}</p>
            </div>
          )}

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}
        </div>
      )}

      {/* Camera Mode */}
      {mode === 'camera' && (
        <div className="space-y-4">
          {/* Camera Selection */}
          <div>
            <label htmlFor="camera-select" className="block text-sm font-medium text-gray-700 mb-2">
              Select Camera
            </label>
            <select
              id="camera-select"
              value={selectedCamera}
              onChange={handleCameraChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {cameras.length === 0 && (
                <option value="">No cameras detected</option>
              )}
              {cameras.map(camera => (
                <option key={camera.deviceId} value={camera.deviceId}>
                  {camera.label || `Camera ${camera.deviceId.substring(0, 8)}`}
                </option>
              ))}
            </select>
          </div>

          {/* Camera Preview */}
          <div className="relative bg-black rounded-lg overflow-hidden" style={{ aspectRatio: '16/9' }}>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-contain"
            />
            {!stream && (
              <div className="absolute inset-0 flex items-center justify-center text-white">
                <div className="text-center">
                  <svg
                    className="mx-auto h-12 w-12 text-gray-400 mb-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                    />
                  </svg>
                  <p className="text-sm">Camera preview will appear here</p>
                </div>
              </div>
            )}
            {recording && (
              <div className="absolute top-4 right-4 flex items-center gap-2 bg-red-600 text-white px-3 py-1 rounded-full">
                <span className="h-2 w-2 bg-white rounded-full animate-pulse"></span>
                <span className="text-sm font-medium">REC</span>
              </div>
            )}
          </div>

          {/* Camera Controls */}
          <div className="flex gap-3">
            {!stream ? (
              <button
                onClick={startCamera}
                disabled={cameras.length === 0}
                className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                Start Camera
              </button>
            ) : (
              <>
                {!recording ? (
                  <button
                    onClick={startRecording}
                    disabled={uploading}
                    className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-300 transition-colors"
                  >
                    Start Recording
                  </button>
                ) : (
                  <button
                    onClick={stopRecording}
                    className="flex-1 px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 transition-colors"
                  >
                    Stop & Upload
                  </button>
                )}
                <button
                  onClick={stopCamera}
                  disabled={recording || uploading}
                  className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 disabled:bg-gray-300 transition-colors"
                >
                  Stop Camera
                </button>
              </>
            )}
          </div>

          {/* Upload Progress */}
          {uploading && (
            <div className="mt-4">
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div
                  className="bg-primary-600 h-2.5 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
              <p className="mt-2 text-sm text-gray-600 text-center">{progress}% uploaded</p>
            </div>
          )}

          {/* Messages */}
          {message && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-md">
              <p className="text-sm text-green-800">{message}</p>
            </div>
          )}

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}
        </div>
      )}

      <div className="mt-4 text-sm text-gray-500">
        <p>💡 <strong>Tip:</strong> The system will automatically process your video and detect suspicious behaviors.</p>
      </div>
    </div>
  );
};

export default VideoUploader;
