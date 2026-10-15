export type Severity = "Minor" | "Moderate" | "Serious" | "Critical";

export type Status = "Open" | "In Progress" | "Resolved";

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: string;
  created_at: string;
}

export interface IssueStatusHistory {
  id: number;
  issue_id: number;
  actor_id: string;
  previous_status: string;
  new_status: string;
  changed_at: string;
  comment?: string | null;
}

export interface Issue {
  id: number;
  owner_id: string;
  title: string;
  description?: string | null;
  page_url: string;
  wcag_criterion?: string | null;
  severity: Severity;
  status: Status;
  version: number;
  created_at: string;
  updated_at: string;
  status_history?: IssueStatusHistory[] | null;
}

export interface PaginatedIssues {
  items: Issue[];
  total: number;
  limit: number;
  offset: number;
}

export interface IssueCreatePayload {
  title: string;
  description?: string | null;
  page_url: string;
  wcag_criterion?: string | null;
  severity: Severity;
}

export interface IssueUpdatePayload {
  title?: string;
  description?: string | null;
  page_url?: string;
  wcag_criterion?: string | null;
  severity?: Severity;
  version: number;
}

export interface IssueStatusUpdatePayload {
  status: Status;
  version: number;
  comment?: string | null;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  fields?: Record<string, string>;
}

export interface ApiErrorEnvelope {
  error: ApiErrorDetail;
}

export class ApiClientError extends Error {
  code: string;
  statusCode: number;
  fields?: Record<string, string>;

  constructor(statusCode: number, detail: ApiErrorDetail) {
    super(detail.message || "An unexpected API error occurred.");
    this.name = "ApiClientError";
    this.statusCode = statusCode;
    this.code = detail.code || "API_ERROR";
    this.fields = detail.fields;
  }
}
