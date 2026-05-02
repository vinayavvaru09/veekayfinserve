export type PolicyType = "Motor" | "Life" | "Medical";

export type NoticeStatus =
  | "pending_automation"
  | "pending_manual_upload"
  | "completed"
  | "failed";

export type NoticeSource = "automated" | "manual_upload" | "reused";

export interface Provider {
  id: string;
  provider_name: string;
  portal_url: string;
}

export interface Policy {
  id: string;
  customer_name: string;
  policy_number: string;
  date_of_birth: string | null;
  phone_number: string | null;
  email: string | null;
  type_of_policy: PolicyType;
  insurance_provider_id: string;
  provider_name: string | null;
  policy_expiry_date: string;
  hold_date: string | null;
  renewed_date: string | null;
}

export interface RenewalNotice {
  id: string;
  policy_id: string;
  policy_number: string;
  policy_expiry_date: string;
  customer_name: string;
  phone_number: string | null;
  email: string | null;
  type_of_policy: PolicyType;
  insurance_provider_id: string;
  provider_name: string | null;
  status: NoticeStatus;
  source: NoticeSource | null;
  document_filename: string | null;
  has_document: boolean;
  created_at: string;
  updated_at: string;
}

export interface MessageTemplate {
  id: string;
  channel: "whatsapp" | "email";
  language: "en" | "te" | null;
  template_key: string;
  subject: string | null;
  body: string;
}

export interface ProcessingLog {
  id: string;
  run_date: string;
  policy_id: string | null;
  policy_number: string | null;
  action: string;
  detail: string | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
