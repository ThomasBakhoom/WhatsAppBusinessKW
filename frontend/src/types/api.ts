export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserResponse {
  id: string;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  avatar_url: string | null;
  is_active: boolean;
  is_verified: boolean;
  roles: string[];
  company_id: string;
  created_at: string;
  updated_at: string;
}

export interface CompanyBriefResponse {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
}

export interface RegisterResponse {
  user: UserResponse;
  tokens: TokenResponse;
}

export interface MeResponse {
  user: UserResponse;
  company: CompanyBriefResponse;
}

export interface PaginatedMeta {
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
  next_cursor: string | null;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginatedMeta;
}

export interface ErrorResponse {
  type: string;
  title: string;
  status: number;
  detail: string | null;
  errors: Array<{ field: string; message: string }> | null;
  trace_id: string | null;
}

export interface SuccessResponse {
  success: boolean;
  message: string;
}

// ── Tags ─────────────────────────────────────────────────────────────────

export interface TagResponse {
  id: string;
  name: string;
  color: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

// ── Custom Fields ────────────────────────────────────────────────────────

export interface CustomFieldResponse {
  id: string;
  name: string;
  label: string;
  field_type: string;
  options: Record<string, unknown> | null;
  is_required: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface CustomFieldValueResponse {
  custom_field_id: string;
  field_name: string;
  field_label: string;
  field_type: string;
  value: string | null;
}

// ── Contacts ─────────────────────────────────────────────────────────────

export interface ContactListItem {
  id: string;
  phone: string;
  email: string | null;
  first_name: string;
  last_name: string;
  full_name: string;
  status: string;
  source: string;
  lead_score: number;
  opt_in_whatsapp: boolean;
  last_contacted_at: string | null;
  assigned_to_user_id: string | null;
  tags: TagResponse[];
  created_at: string;
}

export interface ContactResponse extends ContactListItem {
  avatar_url: string | null;
  notes: string | null;
  custom_fields: CustomFieldValueResponse[];
  company_id: string;
  updated_at: string;
}

export interface ContactCreate {
  phone: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  notes?: string;
  source?: string;
  status?: string;
  opt_in_whatsapp?: boolean;
  tag_ids?: string[];
  assigned_to_user_id?: string;
}

export interface ContactUpdate {
  phone?: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  notes?: string;
  status?: string;
  opt_in_whatsapp?: boolean;
  tag_ids?: string[];
  assigned_to_user_id?: string;
}

export interface ContactImportResponse {
  task_id: string;
  message: string;
}
