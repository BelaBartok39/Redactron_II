import type {
  Batch,
  Document,
  Finding,
  Stats,
  PIITypeCount,
  PaginatedResponse,
} from '../types';

const BASE = '/api';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new ApiError(res.status, body || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  // Batches
  getBatches(): Promise<Batch[]> {
    return request('/batches');
  },

  getBatch(id: string): Promise<Batch> {
    return request(`/batches/${id}`);
  },

  startScan(path: string, options?: { confidence_threshold?: number; worker_count?: number }): Promise<Batch> {
    return request('/scan', {
      method: 'POST',
      body: JSON.stringify({ source_path: path, ...options }),
    });
  },

  deleteBatch(id: string): Promise<void> {
    return request(`/batches/${id}`, { method: 'DELETE' });
  },

  // Documents
  getDocuments(
    batchId: string,
    params?: { page?: number; page_size?: number; pii_type?: string; min_confidence?: number; has_findings?: boolean }
  ): Promise<PaginatedResponse<Document>> {
    const qs = new URLSearchParams();
    if (params?.page) qs.set('page', String(params.page));
    if (params?.page_size) qs.set('page_size', String(params.page_size));
    if (params?.pii_type) qs.set('pii_type', params.pii_type);
    if (params?.min_confidence) qs.set('min_confidence', String(params.min_confidence));
    if (params?.has_findings !== undefined) qs.set('has_findings', String(params.has_findings));
    const query = qs.toString();
    return request(`/batches/${batchId}/documents${query ? `?${query}` : ''}`);
  },

  getDocument(id: string): Promise<Document> {
    return request(`/documents/${id}`);
  },

  // Findings
  getFindings(
    docId: string,
    params?: { page?: number; page_size?: number; pii_type?: string; min_confidence?: number }
  ): Promise<PaginatedResponse<Finding>> {
    const qs = new URLSearchParams();
    if (params?.page) qs.set('page', String(params.page));
    if (params?.page_size) qs.set('page_size', String(params.page_size));
    if (params?.pii_type) qs.set('pii_type', params.pii_type);
    if (params?.min_confidence) qs.set('min_confidence', String(params.min_confidence));
    const query = qs.toString();
    return request(`/documents/${docId}/findings${query ? `?${query}` : ''}`);
  },

  // Stats
  getStats(): Promise<Stats> {
    return request('/stats');
  },

  getPiiTypes(): Promise<PIITypeCount[]> {
    return request('/pii-types');
  },

  // Reports
  generateReport(batchId: string, format: 'pdf' | 'csv'): Promise<{ id: string; status: string }> {
    return request('/reports/generate', {
      method: 'POST',
      body: JSON.stringify({ batch_id: batchId, format }),
    });
  },

  downloadReport(id: string): string {
    return `${BASE}/reports/${id}/download`;
  },
};
