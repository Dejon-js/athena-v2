const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export class ApiService {
  static async request(endpoint: string, options: RequestInit = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }

    return response.json();
  }

  static async getSystemStatus() {
    return this.request('/api/v1/status/system');
  }

  static async getModuleStatus() {
    return this.request('/api/v1/status/modules');
  }

  static async getPerformanceMetrics() {
    return this.request('/api/v1/status/performance');
  }

  static async triggerDataIngestion(dataType: string = 'all') {
    return this.request('/api/v1/data/ingest', {
      method: 'POST',
      body: JSON.stringify({ data_type: dataType }),
    });
  }

  static async getProjectionStatus(week?: number, season: number = 2025) {
    const params = new URLSearchParams();
    if (week) params.append('week', week.toString());
    params.append('season', season.toString());
    
    return this.request(`/api/v1/projections/status?${params}`);
  }

  static async generateProjections(week: number, season: number = 2025) {
    return this.request('/api/v1/projections/generate', {
      method: 'POST',
      body: JSON.stringify({ week, season }),
    });
  }

  static async getOptimizationStatus(optimizationId?: string) {
    const params = new URLSearchParams();
    if (optimizationId) params.append('optimization_id', optimizationId);
    
    return this.request(`/api/v1/optimize/status?${params}`);
  }

  static async optimizeLineups(week: number, season: number = 2025, constraints?: any) {
    return this.request('/api/v1/optimize/lineups', {
      method: 'POST',
      body: JSON.stringify({ week, season, constraints }),
    });
  }

  static async getOptimizedLineups(week: number, season: number = 2025) {
    return this.request(`/api/v1/optimize/lineups?week=${week}&season=${season}`);
  }

  static async askAthena(query: string, context?: any) {
    return this.request('/api/v1/chat/query', {
      method: 'POST',
      body: JSON.stringify({ query, context }),
    });
  }

  static async getQuerySuggestions(week?: number, season: number = 2025) {
    const params = new URLSearchParams();
    if (week) params.append('week', week.toString());
    params.append('season', season.toString());
    
    return this.request(`/api/v1/chat/suggestions?${params}`);
  }

  static async getConversationHistory() {
    return this.request('/api/v1/chat/conversation/history');
  }

  static async exportLineups(week: number, season: number = 2025, format: string = 'csv') {
    return this.request(`/api/v1/optimize/export?week=${week}&season=${season}&format=${format}`);
  }

  static async startScheduler() {
    return this.request('/api/v1/data/scheduler/start', {
      method: 'POST',
    });
  }

  static async stopScheduler() {
    return this.request('/api/v1/data/scheduler/stop', {
      method: 'POST',
    });
  }

  static async getSchedulerStatus() {
    return this.request('/api/v1/data/scheduler/status');
  }
}
