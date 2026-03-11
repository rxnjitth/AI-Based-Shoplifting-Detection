/**
 * TypeScript interfaces for the application.
 */

export interface Alert {
  id: number;
  timestamp: string;
  suspicion_score: number;
  reason: string | null;
  person_bbox: string | null;
  person_confidence: number | null;
  video_path: string;
  snapshot_path: string | null;
  clip_path: string | null;
  status: AlertStatus;
  frame_number: number | null;
  events: Event[];
  behavior_logs: BehaviorLog[];
}

export enum AlertStatus {
  NEW = "new",
  REVIEWED = "reviewed",
  DISMISSED = "dismissed"
}

export interface Event {
  id: number;
  event_type: string;
  timestamp: string;
  event_metadata: string | null;
}

export interface BehaviorLog {
  id: number;
  frame_number: number;
  left_hand_position: string | null;
  right_hand_position: string | null;
  action_type: string | null;
  confidence: number | null;
  zone: string | null;
}

export interface Statistics {
  total_alerts: number;
  total_alerts_today: number;
  average_suspicion_score: number;
  alerts_by_status: {
    [key: string]: number;
  };
  alerts_by_hour: Array<{
    hour: number;
    count: number;
  }>;
  peak_hour: number | null;
}

export interface AlertListResponse {
  total: number;
  alerts: Alert[];
  page: number;
  page_size: number;
}

export interface VideoUploadResponse {
  job_id: string;
  filename: string;
  file_path: string;
  message: string;
}
