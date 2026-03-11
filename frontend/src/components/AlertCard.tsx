/**
 * Alert Card Component
 * Displays a single alert with snapshot, score, and actions.
 */
import React from 'react';
import { Alert, AlertStatus } from '../types';

interface AlertCardProps {
  alert: Alert;
  onClick: () => void;
  onStatusChange: (status: AlertStatus) => void;
}

const AlertCard: React.FC<AlertCardProps> = ({ alert, onClick, onStatusChange }) => {
  const getScoreBadgeClass = (score: number): string => {
    if (score >= 90) return 'badge-danger';
    if (score >= 70) return 'badge-warning';
    return 'badge-success';
  };

  const getStatusBadgeClass = (status: AlertStatus): string => {
    switch (status) {
      case AlertStatus.NEW:
        return 'bg-blue-100 text-blue-800';
      case AlertStatus.REVIEWED:
        return 'bg-green-100 text-green-800';
      case AlertStatus.DISMISSED:
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const getSnapshotUrl = (path: string | null): string => {
    if (!path) return '/placeholder-snapshot.png';
    const filename = path.split('/').pop() || path.split('\\').pop();
    return `http://localhost:8000/evidence/snapshots/${filename}`;
  };

  return (
    <div className="alert-card" onClick={onClick}>
      {/* Snapshot */}
      <div className="mb-3 relative">
        {alert.snapshot_path ? (
          <img
            src={getSnapshotUrl(alert.snapshot_path)}
            alt="Alert snapshot"
            className="w-full h-48 object-cover rounded-md"
            onError={(e) => {
              (e.target as HTMLImageElement).src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect width="400" height="300" fill="%23ddd"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="monospace" font-size="20" fill="%23999"%3ENo Snapshot%3C/text%3E%3C/svg%3E';
            }}
          />
        ) : (
          <div className="w-full h-48 bg-gray-200 rounded-md flex items-center justify-center">
            <span className="text-gray-400">No snapshot available</span>
          </div>
        )}

        {/* Score Badge */}
        <div className="absolute top-2 right-2">
          <span className={`badge ${getScoreBadgeClass(alert.suspicion_score)} text-lg font-bold`}>
            {alert.suspicion_score.toFixed(1)}
          </span>
        </div>
      </div>

      {/* Alert Info */}
      <div className="space-y-2">
        <div className="flex items-start justify-between">
          <h3 className="text-sm font-semibold text-gray-900 line-clamp-2">
            {alert.reason || 'Suspicious activity detected'}
          </h3>
        </div>

        <div className="flex items-center text-xs text-gray-500">
          <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {formatTimestamp(alert.timestamp)}
        </div>

        <div className="flex items-center justify-between">
          <span className={`badge ${getStatusBadgeClass(alert.status)}`}>
            {alert.status}
          </span>

          {alert.events && alert.events.length > 0 && (
            <span className="text-xs text-gray-500">
              {alert.events.length} event{alert.events.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="mt-4 flex gap-2">
        {alert.status === AlertStatus.NEW && (
          <>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onStatusChange(AlertStatus.REVIEWED);
              }}
              className="flex-1 px-3 py-1.5 text-xs bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
            >
              ✓ Review
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onStatusChange(AlertStatus.DISMISSED);
              }}
              className="flex-1 px-3 py-1.5 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
            >
              ✕ Dismiss
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default AlertCard;
