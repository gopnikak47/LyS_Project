/** Kiểu dữ liệu trả về từ API (khớp schema Pydantic phía backend). */
import type { Industry, TenantRole as Role } from "@lys/shared";

export type Permission =
  | "report:view"
  | "survey:edit"
  | "label:edit"
  | "label:approve"
  | "data:export"
  | "topic:manage"
  | "member:manage"
  | "workspace:manage"
  | "tenant:manage";

export type UserOut = { id: string; email: string; full_name: string; locale: string };
export type TenantOut = {
  id: string;
  name: string;
  slug: string;
  industry: Industry | null;
  plan_code: string;
};
export type MembershipSummary = {
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  role: Role;
};

export type Session = {
  user: UserOut;
  tenant: TenantOut;
  role: Role;
  permissions: Permission[];
  all_workspaces: boolean;
  workspace_ids: string[];
  memberships: MembershipSummary[];
  csrf_token: string | null;
  access_expires_at: string | null;
};

export type WorkspaceSettings = {
  urgent_keywords: string[];
  topic_threshold: number;
  alert_emails: string[];
};

export type Workspace = {
  id: string;
  name: string;
  description: string | null;
  industry: Industry | null;
  color: string;
  settings: Partial<WorkspaceSettings>;
  survey_count: number;
  created_at: string;
};

export type Member = {
  id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: Role;
  status: "active" | "disabled";
  all_workspaces: boolean;
  workspace_ids: string[];
  last_login_at: string | null;
  created_at: string;
};

export type Invitation = {
  id: string;
  email: string;
  role: Role;
  workspace_ids: string[];
  expires_at: string;
  created_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
};

export type InvitationCreated = Invitation & { invite_url: string };

export type PublicInvitation = {
  tenant_name: string;
  email: string;
  role: Role;
  inviter_name: string | null;
  user_exists: boolean;
  expires_at: string;
};

export type Topic = {
  id: string;
  name: string;
  description: string | null;
  keywords: string[];
  color: string;
  sort_order: number;
  is_active: boolean;
  usage_count: number;
};

export type TopicSet = {
  id: string;
  workspace_id: string;
  name: string;
  template_code: string | null;
  version: number;
  topics: Topic[];
};

export type TopicTemplate = {
  code: string;
  name: string;
  topics: { name: string; description: string; keywords: string[]; color: string }[];
};
