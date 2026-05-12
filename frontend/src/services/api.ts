/**
 * API client for backend communication.
 */
import axios from 'axios';
import { Alert, AlertListResponse, Statistics, AlertStatus, VideoUploadResponse } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const alertsApi = {
  /**
   * Get list of alerts with optional filtering.
   */
  getAlerts: async (params?: {
    page?: number;
    page_size?: number;
    status?: AlertStatus;
    min_score?: number;
    from_date?: string;
    to_date?: string;
  }): Promise<AlertListResponse> => {
    const response = await api.get('/api/alerts/', { params });
    return response.data;
  },

  /**
   * Get single alert by ID.
   */
  getAlert: async (id: number): Promise<Alert> => {
    const response = await api.get(`/api/alerts/${id}`);
    return response.data;
  },

  /**
   * Update alert status.
   */
  updateAlert: async (id: number, data: { status?: AlertStatus; reason?: string }): Promise<Alert> => {
    const response = await api.patch(`/api/alerts/${id}`, data);
    return response.data;
  },

  /**
   * Delete alert.
   */
  deleteAlert: async (id: number): Promise<void> => {
    await api.delete(`/api/alerts/${id}`);
  },
};

export const statsApi = {
  /**
   * Get dashboard statistics.
   */
  getStatistics: async (params?: {
    from_date?: string;
    to_date?: string;
  }): Promise<Statistics> => {
    const response = await api.get('/api/stats/', { params });
    return response.data;
  },
};

export const videosApi = {
  /**
   * Upload video for processing.
   */
  uploadVideo: async (file: File, onProgress?: (progress: number) => void): Promise<VideoUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/api/videos/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });

    return response.data;
  },

  /**
   * Get job status.
   */
  getJobStatus: async (jobId: string): Promise<any> => {
    const response = await api.get(`/api/videos/status/${jobId}`);
    return response.data;
  },
};

export const liveApi = {
  /**
   * Detect objects in a single frame (base64 encoded).
   * session_id must be stable for the duration of a camera session.
   */
  detectFrame: async (imageData: string, sessionId: string = 'default'): Promise<any> => {
    const response = await api.post('/api/live/detect-frame-base64', {
      image: imageData,
      session_id: sessionId,
    });
    return response.data;
  },

  /**
   * End a live detection session and release backend state.
   */
  endSession: async (sessionId: string): Promise<void> => {
    await api.delete(`/api/live/session/${sessionId}`);
  },
};

export const rtspApi = {
  connect: async (payload: {
    camera_id: string;
    rtsp_url?: string;
    ip?: string;
    port?: number;
    username?: string;
    password?: string;
    channel?: number;
    stream?: string;
  }): Promise<any> => {
    const response = await api.post('/api/rtsp/connect', payload);
    return response.data;
  },

  disconnect: async (cameraId: string): Promise<void> => {
    await api.delete(`/api/rtsp/disconnect/${cameraId}`);
  },

  getStatus: async (cameraId: string): Promise<any> => {
    const response = await api.get(`/api/rtsp/status/${cameraId}`);
    return response.data;
  },

  listCameras: async (): Promise<any> => {
    const response = await api.get('/api/rtsp/cameras');
    return response.data;
  },

  getDefaultCamera: async (): Promise<any> => {
    const response = await api.get('/api/rtsp/default-camera');
    return response.data;
  },
};

export default api;
