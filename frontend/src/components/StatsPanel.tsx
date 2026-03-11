/**
 * Statistics Panel Component
 * Displays dashboard analytics and metrics.
 */
import React, { useState, useEffect } from 'react';
import { statsApi } from '../services/api';
import { Statistics } from '../types';

const StatsPanel: React.FC = () => {
  const [stats, setStats] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    try {
      const data = await statsApi.getStatistics();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch statistics:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();

    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-24 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-4">Dashboard Statistics</h2>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {/* Total Alerts */}
        <div className="stat-card">
          <div className="text-sm text-gray-500 mb-1">Total Alerts</div>
          <div className="text-3xl font-bold text-gray-900">{stats.total_alerts}</div>
        </div>

        {/* Alerts Today */}
        <div className="stat-card">
          <div className="text-sm text-gray-500 mb-1">Alerts Today</div>
          <div className="text-3xl font-bold text-primary-600">{stats.total_alerts_today}</div>
        </div>

        {/* Average Score */}
        <div className="stat-card">
          <div className="text-sm text-gray-500 mb-1">Avg. Suspicion Score</div>
          <div className="text-3xl font-bold text-yellow-600">
            {stats.average_suspicion_score.toFixed(1)}
          </div>
        </div>

        {/* Peak Hour */}
        <div className="stat-card">
          <div className="text-sm text-gray-500 mb-1">Peak Hour</div>
          <div className="text-3xl font-bold text-danger-600">
            {stats.peak_hour !== null ? `${stats.peak_hour}:00` : 'N/A'}
          </div>
        </div>
      </div>

      {/* Alerts by Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Status Breakdown */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Alerts by Status</h3>
          <div className="space-y-3">
            {Object.entries(stats.alerts_by_status).map(([status, count]) => {
              const total = stats.total_alerts || 1;
              const percentage = ((count / total) * 100).toFixed(0);

              const statusColors: { [key: string]: string } = {
                new: 'bg-red-500',
                reviewed: 'bg-yellow-500',
                dismissed: 'bg-green-500'
              };

              return (
                <div key={status}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700 capitalize">
                      {status}
                    </span>
                    <span className="text-sm text-gray-600">
                      {count} ({percentage}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`${statusColors[status]} h-2 rounded-full transition-all`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Alerts by Hour */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Alerts by Hour</h3>
          <div className="flex items-end justify-between h-32 gap-1">
            {stats.alerts_by_hour.length > 0 ? (
              stats.alerts_by_hour.map((item) => {
                const maxCount = Math.max(...stats.alerts_by_hour.map(a => a.count), 1);
                const heightPercent = (item.count / maxCount) * 100;

                return (
                  <div
                    key={item.hour}
                    className="flex-1 group relative"
                  >
                    <div
                      className="bg-primary-500 hover:bg-primary-600 transition-all rounded-t"
                      style={{ height: `${heightPercent}%`, minHeight: item.count > 0 ? '4px' : '0' }}
                    ></div>
                    <div className="text-xs text-gray-500 text-center mt-1">
                      {item.hour}h
                    </div>
                    {/* Tooltip */}
                    <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity bg-gray-900 text-white text-xs rounded py-1 px-2 whitespace-nowrap">
                      {item.count} alerts
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="flex-1 text-center text-gray-400 text-sm">
                No data available
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatsPanel;
