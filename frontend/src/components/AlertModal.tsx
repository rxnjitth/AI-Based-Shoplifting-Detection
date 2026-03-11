/**
 * Alert Modal Component
 * Displays detailed information about an alert with video clip playback.
 */
import React from 'react';
import { Alert, AlertStatus } from '../types';

interface AlertModalProps {
  alert: Alert;
  isOpen: boolean;
  onClose: () => void;
  onStatusChange: (status: AlertStatus) => void;
}

const AlertModal: React.FC<AlertModalProps> = ({ alert, isOpen, onClose, onStatusChange }) => {
  const [annotatedLoadFailed, setAnnotatedLoadFailed] = React.useState(false);

  React.useEffect(() => {
    if (isOpen) {
      setAnnotatedLoadFailed(false);
    }
  }, [isOpen, alert.id]);

  if (!isOpen) return null;

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const getSnapshotUrl = (path: string | null): string | null => {
    if (!path) return null;
    const filename = path.split('/').pop() || path.split('\\').pop();
    const apiBase = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    return `${apiBase}/evidence/snapshots/${filename}`;
  };

  const getAnnotatedVideoUrl = (videoPath: string): string | null => {
    const filename = videoPath.split('/').pop() || videoPath.split('\\').pop();
    if (!filename) return null;

    const dotIndex = filename.lastIndexOf('.');
    const jobId = dotIndex > 0 ? filename.slice(0, dotIndex) : filename;
    if (!jobId) return null;

    const apiBase = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    return `${apiBase}/api/videos/annotated/${jobId}`;
  };

  const annotatedVideoUrl = getAnnotatedVideoUrl(alert.video_path);

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" onClick={onClose}>
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"></div>

        {/* Modal panel */}
        <div
          className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="bg-white px-6 py-4 border-b">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                Alert Details - ID: {alert.id}
              </h3>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="bg-white px-6 py-4 space-y-4">
            {/* Detection video with tracked IDs (preferred evidence). */}
            {annotatedVideoUrl && !annotatedLoadFailed && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Detection Video (Tracked IDs)</h4>
                <video
                  controls
                  preload="metadata"
                  className="w-full rounded-lg shadow"
                  src={annotatedVideoUrl}
                  onError={() => setAnnotatedLoadFailed(true)}
                >
                  Your browser does not support the video tag.
                </video>
              </div>
            )}

            {(!annotatedVideoUrl || annotatedLoadFailed) && (
              <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
                Detection video is unavailable for this alert. Re-process the source video to generate a browser-playable annotated output.
              </p>
            )}

            {alert.snapshot_path && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Alert Snapshot</h4>
                <img
                  src={getSnapshotUrl(alert.snapshot_path) || undefined}
                  alt="Alert snapshot"
                  className="w-full rounded-lg shadow"
                />
              </div>
            )}

            {/* Alert Information */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-gray-500">Suspicion Score</p>
                <p className="text-2xl font-bold text-danger-600">{alert.suspicion_score.toFixed(1)}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Status</p>
                <p className="text-lg font-semibold capitalize">{alert.status}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Timestamp</p>
                <p className="text-sm">{formatTimestamp(alert.timestamp)}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Frame Number</p>
                <p className="text-sm">{alert.frame_number || 'N/A'}</p>
              </div>
            </div>

            {/* Reason */}
            {alert.reason && (
              <div>
                <p className="text-sm font-medium text-gray-500 mb-1">Reason</p>
                <p className="text-sm text-gray-900">{alert.reason}</p>
              </div>
            )}

            {/* Events Timeline */}
            {alert.events && alert.events.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Events ({alert.events.length})</h4>
                <div className="space-y-2">
                  {alert.events.map((event) => (
                    <div key={event.id} className="flex items-start gap-2 text-sm">
                      <span className="inline-block w-2 h-2 mt-1.5 rounded-full bg-primary-600"></span>
                      <div>
                        <p className="font-medium">{event.event_type}</p>
                        {event.event_metadata && (
                          <p className="text-xs text-gray-500">{event.event_metadata}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="bg-gray-50 px-6 py-4 flex gap-3 justify-end">
            {alert.status === AlertStatus.NEW && (
              <>
                <button
                  onClick={() => onStatusChange(AlertStatus.REVIEWED)}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  Mark as Reviewed
                </button>
                <button
                  onClick={() => onStatusChange(AlertStatus.DISMISSED)}
                  className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                >
                  Dismiss
                </button>
              </>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 bg-white text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AlertModal;
