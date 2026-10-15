import {
  ApiClientError,
  ApiErrorEnvelope,
  Issue,
  IssueCreatePayload,
  IssueStatusUpdatePayload,
  IssueUpdatePayload,
  PaginatedIssues,
  Severity,
  Status,
  User,
} from "./types";

const DEMO_USER_STORAGE_KEY = "ua_demo_user_id";
export const DEFAULT_DEMO_USER_ID = "demo-user-alice";

export function getStoredDemoUserId(): string {
  try {
    return localStorage.getItem(DEMO_USER_STORAGE_KEY) || DEFAULT_DEMO_USER_ID;
  } catch {
    return DEFAULT_DEMO_USER_ID;
  }
}

export function setStoredDemoUserId(userId: string): void {
  try {
    localStorage.setItem(DEMO_USER_STORAGE_KEY, userId);
  } catch {
    // Ignore storage errors if localStorage is disabled
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const currentDemoUserId = getStoredDemoUserId();
  const headers = new Headers(options.headers || {});

  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  if (!headers.has("Content-Type") && options.body && typeof options.body === "string") {
    headers.set("Content-Type", "application/json");
  }

  // Always supply the chosen local demo identity header
  headers.set("X-Demo-User-Id", currentDemoUserId);

  let response: Response;
  try {
    response = await fetch(endpoint, {
      ...options,
      headers,
    });
  } catch (networkErr: unknown) {
    throw new ApiClientError(0, {
      code: "NETWORK_ERROR",
      message: "Unable to connect to the backend server. Please verify the API is running at http://127.0.0.1:8000.",
    });
  }

  if (response.ok) {
    if (response.status === 204) {
      return {} as T;
    }
    return (await response.json()) as T;
  }

  // Handle error responses from backend
  let errorPayload: ApiErrorEnvelope | null = null;
  try {
    errorPayload = (await response.json()) as ApiErrorEnvelope;
  } catch {
    // Non-JSON response
  }

  if (errorPayload && errorPayload.error) {
    throw new ApiClientError(response.status, errorPayload.error);
  }

  throw new ApiClientError(response.status, {
    code: `HTTP_${response.status}`,
    message: response.statusText || `Request failed with status ${response.status}`,
  });
}

export const api = {
  async getCurrentUser(): Promise<User> {
    return request<User>("/api/me");
  },

  async getDemoUsers(): Promise<User[]> {
    return request<User[]>("/api/users/demo");
  },

  async getIssues(params?: {
    status?: Status;
    severity?: Severity;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedIssues> {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.severity) query.set("severity", params.severity);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset !== undefined) query.set("offset", String(params.offset));

    const qs = query.toString();
    return request<PaginatedIssues>(`/api/issues${qs ? `?${qs}` : ""}`);
  },

  async getIssue(id: number): Promise<Issue> {
    return request<Issue>(`/api/issues/${id}`);
  },

  async createIssue(payload: IssueCreatePayload): Promise<Issue> {
    return request<Issue>("/api/issues", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async updateIssue(id: number, payload: IssueUpdatePayload): Promise<Issue> {
    return request<Issue>(`/api/issues/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  async updateIssueStatus(id: number, payload: IssueStatusUpdatePayload): Promise<Issue> {
    return request<Issue>(`/api/issues/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
};
