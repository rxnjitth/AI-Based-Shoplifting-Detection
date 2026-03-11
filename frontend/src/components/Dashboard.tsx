/**
 * Main Dashboard Component
 * Integrates all dashboard features: video upload, alerts, timeline, and statistics.
 */
import React, { useState, useEffect, useCallback } from 'react';
import VideoUploader from './VideoUploader';
import LiveDetection from './LiveDetection';
import AlertCard from './AlertCard';
import EventTimeline from './EventTimeline';
import StatsPanel from './StatsPanel';
import AlertModal from './AlertModal';
import VideoPlayer from './VideoPlayer';
import { alertsApi } from '../services/api';
import { Alert, AlertStatus } from '../types';

const Dashboard: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<AlertStatus | 'all'>('all');
  const [minScore, setMinScore] = useState<number>(0);
  const [videoJobId, setVideoJobId] = useState<string>('');
  const [showVideoPlayer, setShowVideoPlayer] = useState(false);
  const [inputMode, setInputMode] = useState<'upload' | 'live'>('live'); // Default to live detection

  // Fetch alerts
  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      const params: any = {
        page: 1,
        page_size: 50,
      };
      
      if (filterStatus !== 'all') {
        params.status = filterStatus;
      }
      
      if (minScore > 0) {
        params.min_score = minScore;
      }

      const response = await alertsApi.getAlerts(params);
      setAlerts(response.alerts);
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    } finally {
      setLoading(false);
    }
  }, [filterStatus, minScore]);

  useEffect(() => {
    fetchAlerts();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  const handleAlertClick = (alert: Alert) => {
    setSelectedAlert(alert);
    setIsModalOpen(true);
  };

  const handleStatusUpdate = async (alertId: number, status: AlertStatus) => {
    try {
      await alertsApi.updateAlert(alertId, { status });
      fetchAlerts();
    } catch (error) {
      console.error('Failed to update alert:', error);
    }
  };

  const handleVideoUploaded = (jobId: string) => {
    // Open video player with live detection
    setVideoJobId(jobId);
    setShowVideoPlayer(true);
    
    // Refresh alerts after a delay to allow processing
    setTimeout(fetchAlerts, 5000);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Input Mode Tabs */}
      <div className="mb-6">
        <div className="bg-white rounded-lg shadow p-1 inline-flex">
          <button
            onClick={() => setInputMode('live')}
            className={`px-6 py-3 rounded-md font-semibold transition-all ${
              inputMode === 'live'
                ? 'bg-primary-600 text-white shadow'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            📹 Live Detection
          </button>
          <button
            onClick={() => setInputMode('upload')}
            className={`px-6 py-3 rounded-md font-semibold transition-all ${
              inputMode === 'upload'
                ? 'bg-primary-600 text-white shadow'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            📁 Upload Video
          </button>
        </div>
      </div>

      {/* Live Detection Section */}
      {inputMode === 'live' && (
        <div className="mb-8">
          <LiveDetection />
        </div>
      )}

      {/* Video Upload Section */}
      {inputMode === 'upload' && (
        <div className="mb-8">
          <VideoUploader onUploadSuccess={handleVideoUploaded} />
        </div>
      )}

      {/* Statistics Panel */}
      <div className="mb-8">
        <StatsPanel />
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-center">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Filter by Status
            </label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as AlertStatus | 'all')}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="all">All Statuses</option>
              <option value={AlertStatus.NEW}>New</option>
              <option value={AlertStatus.REVIEWED}>Reviewed</option>
              <option value={AlertStatus.DISMISSED}>Dismissed</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Minimum Score
            </label>
            <input
              type="number"
              min="0"
              max="100"
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="0"
            />
          </div>

          <div className="ml-auto">
            <button
              onClick={fetchAlerts}
              className="btn-primary"
            >
              🔄 Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Event Timeline */}
      {alerts.length > 0 && (
        <div className="mb-8">
          <EventTimeline alerts={alerts} onAlertClick={handleAlertClick} />
        </div>
      )}

      {/* Alerts Grid */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Recent Alerts ({alerts.length})
        </h2>

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            <p className="mt-4 text-gray-600">Loading alerts...</p>
          </div>
        ) : alerts.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <p className="text-gray-500 text-lg">No alerts found</p>
            <p className="text-gray-400 mt-2">Upload a video to start detecting suspicious behavior</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {alerts.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                onClick={() => handleAlertClick(alert)}
                onStatusChange={(status) => handleStatusUpdate(alert.id, status)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Alert Detail Modal */}
      {selectedAlert && (
        <AlertModal
          alert={selectedAlert}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onStatusChange={(status) => {
            handleStatusUpdate(selectedAlert.id, status);
            setIsModalOpen(false);
          }}
        />
      )}

      {/* Video Player with Live Detection */}
      {showVideoPlayer && videoJobId && (
        <VideoPlayer
          jobId={videoJobId}
          onClose={() => setShowVideoPlayer(false)}
        />
      )}
    </div>
  );
};

export default Dashboard;
