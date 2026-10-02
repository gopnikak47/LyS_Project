"use client";

import { useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "./client";
import type { Permission, Session, Workspace } from "./types";

export const queryKeys = {
  session: ["session"] as const,
  workspaces: ["workspaces"] as const,
  members: ["members"] as const,
  invitations: ["invitations"] as const,
};

// ------------------------------------------------------------------ phiên đăng nhập
export function useSession() {
  return useQuery({
    queryKey: queryKeys.session,
    queryFn: () => api<Session>("/auth/me"),
    staleTime: 60_000,
  });
}

export function useCan(permission: Permission): boolean {
  const { data } = useSession();
  return !!data?.permissions.includes(permission);
}

export function useLogout() {
  const router = useRouter();
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api("/auth/logout", { method: "POST" }),
    onSettled: () => {
      client.clear();
      router.replace("/login");
    },
  });
}

export function useSwitchTenant() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (tenantId: string) =>
      api<Session>("/auth/switch-tenant", { method: "POST", body: { tenant_id: tenantId } }),
    onSuccess: (session) => {
      setSelectedWorkspace(null);
      client.clear();
      client.setQueryData(queryKeys.session, session);
    },
  });
}

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

// ------------------------------------------------------------------ workspace đang chọn
const STORAGE_KEY = "lys.workspace";
const listeners = new Set<() => void>();

function readSelected(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setSelectedWorkspace(id: string | null) {
  try {
    if (id) localStorage.setItem(STORAGE_KEY, id);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // localStorage bị chặn: chỉ giữ lựa chọn trong phiên hiện tại.
  }
  listeners.forEach((fn) => fn());
}

function subscribe(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function useWorkspaces() {
  return useQuery({
    queryKey: queryKeys.workspaces,
    queryFn: () => api<Workspace[]>("/workspaces"),
  });
}

/** Workspace hiện tại: lựa chọn đã lưu nếu còn quyền truy cập, ngược lại workspace đầu tiên. */
export function useCurrentWorkspace() {
  const selected = useSyncExternalStore(subscribe, readSelected, () => null);
  const query = useWorkspaces();
  const workspaces = query.data ?? [];
  const workspace = workspaces.find((w) => w.id === selected) ?? workspaces[0] ?? null;
  return { workspace, workspaces, isLoading: query.isLoading, error: query.error };
}
