// API client for frontend
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface Event {
  id: number;
  gotsport_event_id: string;
  name: string;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  url: string;
  status: string;
  last_scraped_at: string | null;
  created_at: string;
  updated_at: string;
  total_divisions?: number;
  total_teams?: number;
  total_games?: number;
  next_scrape_in_hours?: number;
}

export interface Division {
  id: number;
  event_id: number;
  name: string;
  age_group: string | null;
  gender: string | null;
  gotsport_division_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Game {
  id: number;
  division_id: number;
  gotsport_game_id: string | null;
  game_number: string | null;
  home_team_id: number | null;
  away_team_id: number | null;
  home_team_name: string | null;
  away_team_name: string | null;
  game_date: string | null;
  game_time: string | null;
  field_name: string | null;
  field_location: string | null;
  home_score: number | null;
  away_score: number | null;
  status: string;
  created_at: string;
  updated_at: string;
  division_name?: string;
  event_name?: string;
}

export interface Schedule {
  event: Event;
  divisions: Division[];
  games: Game[];
  total_games: number;
}

// API functions
export const eventsApi = {
  getAll: () => apiClient.get<Event[]>('/events/'),
  getById: (id: number) => apiClient.get<Event>(`/events/${id}`),
  create: (data: Partial<Event>) => apiClient.post<Event>('/events/', data),
  update: (id: number, data: Partial<Event>) => apiClient.patch<Event>(`/events/${id}`, data),
  delete: (id: number) => apiClient.delete(`/events/${id}`),
};

export const schedulesApi = {
  getEventSchedule: (eventId: number, params?: {
    division_id?: number;
    date_from?: string;
    date_to?: string;
    field_name?: string;
    team_name?: string;
    status?: string;
  }) => apiClient.get<Schedule>(`/schedules/${eventId}`, { params }),
};

export const scrapingApi = {
  trigger: (eventId: number, force: boolean = false) =>
    apiClient.post('/scraping/trigger', { event_id: eventId, force }),
  getStatus: () => apiClient.get('/scraping/status'),
  getLogs: (eventId: number, limit: number = 10) =>
    apiClient.get(`/scraping/logs/${eventId}`, { params: { limit } }),
};
