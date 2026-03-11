/**
 * Event Timeline Component
 * Visualizes alerts on a timeline with suspicion scores.
 */
import React from 'react';
import { Alert } from '../types';

interface EventTimelineProps {
  alerts: Alert[];
  onAlertClick: (alert: Alert) => void;
}

const EventTimeline: React.FC<EventTimelineProps> = ({ alerts, onAlertClick }) => {
  if (alerts.length === 0) return null;

  // Sort alerts by timestamp
  const sortedAlerts = [...alerts].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  const formatTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getScoreColor = (score: number): string => {
    if (score >= 90) return 'bg-red-500';
    if (score >= 70) return 'bg-orange-500';
    return 'bg-yellow-500';
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">Event Timeline</h2>

      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-gray-200"></div>

        {/* Events */}
        <div className="space-y-6">
          {sortedAlerts.map((alert, index) => (
            <div
              key={alert.id}
              className="relative pl-8 cursor-pointer hover:bg-gray-50 p-2 rounded transition-colors"
              onClick={() => onAlertClick(alert)}
            >
              {/* Timeline marker */}
              <div
                className={`absolute left-0 top-3 w-3 h-3 rounded-full ${getScoreColor(alert.suspicion_score)} -ml-1.5 ring-4 ring-white`}
              ></div>

              {/* Content */}
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-gray-900">
                      {formatTime(alert.timestamp)}
                    </span>
                    <span className="text-xs text-gray-500">
                      Alert #{alert.id}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">
                    {alert.reason || 'Suspicious activity detected'}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span className={`badge ${
                    alert.suspicion_score >= 90 ? 'badge-danger' :
                    alert.suspicion_score >= 70 ? 'badge-warning' :
                    'badge-success'
                  }`}>
                    {alert.suspicion_score.toFixed(0)}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default EventTimeline;
