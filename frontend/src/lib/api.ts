/**
 * API Client — Centralized HTTP client for the PDF Search Platform backend.
 */

let apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// If Render passes just the host (e.g. "pdf-backend-xyz.onrender.com"), prepend https://
if (apiBaseUrl && !apiBaseUrl.startsWith('http')) {
  apiBaseUrl = `https://${apiBaseUrl}`;
}

if (apiBaseUrl && !apiBaseUrl.endsWith('/api/v1')) {
  // Remove trailing slash if it exists before appending
  apiBaseUrl = apiBaseUrl.replace(/\/$/, '') + '/api/v1';
}
const API_BASE = apiBaseUrl;
interface FetchOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string | null) {
    this.token = token;
  }

  private buildUrl(path: string, params?: Record<string, string | number | boolean | undefined>): string {
    const url = new URL(`${this.baseUrl}${path}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.set(key, String(value));
        }
      });
    }
    return url.toString();
  }

  private async request<T>(path: string, options: FetchOptions = {}): Promise<T> {
    const { params, ...fetchOptions } = options;
    const url = this.buildUrl(path, params);

    const headers: Record<string, string> = {
      ...(fetchOptions.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    if (!(fetchOptions.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, {
      ...fetchOptions,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new ApiError(response.status, error.detail || 'Request failed');
    }

    const text = await response.text();
    return text ? JSON.parse(text) : (null as unknown as T);
  }

  // ── Upload ──

  async uploadPdf(file: File, onProgress?: (progress: number) => void): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    // Use XMLHttpRequest for progress tracking
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${this.baseUrl}/upload`);

      if (this.token) {
        xhr.setRequestHeader('Authorization', `Bearer ${this.token}`);
      }

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else {
          reject(new ApiError(xhr.status, 'Upload failed'));
        }
      };

      xhr.onerror = () => reject(new ApiError(0, 'Network error'));
      xhr.send(formData);
    });
  }

  async uploadBatch(files: File[]): Promise<UploadResponse[]> {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));

    return this.request<UploadResponse[]>('/upload/batch', {
      method: 'POST',
      body: formData,
    });
  }

  async getUploadStatus(documentId: string): Promise<UploadStatusResponse> {
    return this.request<UploadStatusResponse>(`/upload/status/${documentId}`);
  }

  // ── Documents ──

  async getDocuments(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    language?: string;
    search?: string;
  }): Promise<DocumentListResponse> {
    return this.request<DocumentListResponse>('/documents', { params });
  }

  async getDocument(id: string): Promise<DocumentDetail> {
    return this.request<DocumentDetail>(`/documents/${id}`);
  }

  async getDocumentFile(id: string): Promise<{ file_path: string }> {
    return this.request<{ file_path: string }>(`/documents/${id}/file`);
  }

  async getPage(documentId: string, pageNumber: number): Promise<PageDetail> {
    return this.request<PageDetail>(`/documents/${documentId}/page/${pageNumber}`);
  }

  async deleteDocument(id: string): Promise<void> {
    return this.request(`/documents/${id}`, { method: 'DELETE' });
  }

  async getStats(): Promise<PlatformStats> {
    return this.request<PlatformStats>('/documents/stats');
  }

  // ── Search ──

  async search(params: SearchParams): Promise<SearchResponse> {
    return this.request<SearchResponse>('/search', {
      params: params as unknown as Record<string, string | number | boolean>,
    });
  }

  async getSuggestions(query: string): Promise<{ suggestions: string[] }> {
    return this.request<{ suggestions: string[] }>('/search/suggestions', {
      params: { q: query },
    });
  }

  // ── Auth ──

  async login(username: string, password: string): Promise<TokenResponse> {
    return this.request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  }

  async register(data: RegisterData): Promise<UserResponse> {
    return this.request<UserResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ── Health ──

  async healthCheck(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }
}

// ── Error Class ──

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

// ── Types ──

export interface UploadResponse {
  document_id: string;
  filename: string;
  file_size: number;
  task_id: string | null;
  message: string;
}

export interface UploadStatusResponse {
  document_id: string;
  status: string;
  progress: number;
  message: string | null;
  error: string | null;
}

export interface DocumentListResponse {
  documents: DocumentSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DocumentSummary {
  id: string;
  filename: string;
  original_filename: string;
  file_size: number;
  page_count: number;
  author: string | null;
  title: string | null;
  upload_date: string;
  primary_language: string | null;
  processing_status: string;
  processing_progress: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends DocumentSummary {
  subject: string | null;
  creation_date: string | null;
  processing_error: string | null;
  pages: PageSummary[];
  metadata_json: Record<string, unknown> | null;
}

export interface PageSummary {
  id: string;
  document_id: string;
  page_number: number;
  extracted_text: string | null;
  language: string | null;
  has_text_layer: boolean;
  ocr_applied: boolean;
  word_count: number;
  page_width: number | null;
  page_height: number | null;
}

export interface PageDetail extends PageSummary {
  text_blocks: TextBlock[];
}

export interface TextBlock {
  id: string;
  block_index: number;
  text_content: string;
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number | null;
  font_name: string | null;
  font_size: number | null;
}

export interface SearchParams {
  q: string;
  search_type?: string;
  page?: number;
  page_size?: number;
  language?: string;
  filename?: string;
  date_from?: string;
  date_to?: string;
  fuzzy?: boolean;
}

export interface SearchResponse {
  query: string;
  search_type: string;
  total_hits: number;
  hits: SearchHit[];
  page: number;
  page_size: number;
  total_pages: number;
  took_ms: number;
  suggestions: string[];
}

export interface SearchHit {
  document_id: string;
  page_id: string;
  filename: string;
  page_number: number;
  content_snippet: string;
  highlighted_content: string;
  language: string | null;
  author: string | null;
  upload_date: string | null;
  word_count: number;
  score: number;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface RegisterData {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface UserResponse {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface PlatformStats {
  total_documents: number;
  total_pages: number;
  completed_documents: number;
  processing_documents: number;
  pending_documents: number;
  total_storage_bytes: number;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
  elasticsearch: string;
}

// ── Export singleton instance ──

export const api = new ApiClient(API_BASE);
export default api;
