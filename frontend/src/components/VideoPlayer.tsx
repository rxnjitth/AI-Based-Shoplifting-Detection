import React, { useEffect, useState } from 'react';

interface JobStatusResponse {
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'unknown';
  message?: string;
}

interface VideoPlayerProps {
  jobId: string;
  onClose: () => void;
}

const VideoPlayer: React.FC<VideoPlayerProps> = ({ jobId, onClose }) => {
  const [videoUrl, setVideoUrl] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    let isActive = true;
    let retries = 0;
    const maxRetries = 90; // ~3 minutes at 2s intervals

    const checkVideo = async () => {
      if (!isActive) return;

      const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const statusUrl = `${baseUrl}/api/videos/status/${jobId}`;
      const videoUrl = `${baseUrl}/api/videos/annotated/${jobId}`;
      
      try {
        const response = await fetch(statusUrl);

        if (!response.ok) {
          setError('Failed to get video processing status');
          setIsLoading(false);
          return;
        }

        const statusData: JobStatusResponse = await response.json();

        if (statusData.status === 'completed') {
          if (!isActive) return;
          setVideoUrl(videoUrl);
          setIsLoading(false);
        } else if (statusData.status === 'failed') {
          setError(statusData.message || 'Video processing failed. Please re-upload and try again.');
          setIsLoading(false);
        } else if (statusData.status === 'queued' || statusData.status === 'processing') {
          retries += 1;
          if (retries >= maxRetries) {
            setError('Video processing is taking too long or failed. Please re-upload and try again.');
            setIsLoading(false);
            return;
          }
          timeoutId = setTimeout(checkVideo, 2000);
        } else {
          setError('Job not found. Please upload the video again.');
          setIsLoading(false);
        }
      } catch (err) {
        setError('Failed to connect to server');
        setIsLoading(false);
      }
    };

    checkVideo();

    return () => {
      isActive = false;
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [jobId]);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full mx-4 max-h-[90vh] overflow-auto">
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b">
          <h2 className="text-xl font-bold">Live Theft Detection</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl font-bold w-8 h-8 flex items-center justify-center"
          >
            ×
          </button>
        </div>

        {/* Video Player */}
        <div className="p-6">
          {isLoading && (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Processing video with detection overlays...</p>
              <p className="text-sm text-gray-500 mt-2">This may take a moment</p>
            </div>
          )}

          {error && (
            <div className="text-center py-12">
              <p className="text-red-600">{error}</p>
            </div>
          )}

          {videoUrl && !isLoading && !error && (
            <div>
              <video
                className="w-full rounded-lg shadow-lg"
                controls
                autoPlay
                src={videoUrl}
              >
                Your browser does not support the video tag.
              </video>
              
              <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                <h3 className="font-semibold text-blue-900 mb-2">Detection Legend:</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="flex items-center">
                    <div className="w-4 h-4 bg-green-500 mr-2"></div>
                    <span>Normal Behavior</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-4 h-4 bg-red-500 mr-2"></div>
                    <span>Suspicious Activity Detected</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-4 h-4 bg-purple-500 mr-2 rounded-full"></div>
                    <span>Pose Landmarks</span>
                  </div>
                  <div className="flex items-center">
                    <div className="w-4 h-4 bg-cyan-400 mr-2"></div>
                    <span>Skeleton Tracking</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default VideoPlayer;
