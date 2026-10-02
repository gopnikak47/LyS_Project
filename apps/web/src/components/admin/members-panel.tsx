"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";
import { TENANT_ROLES } from "@lys/shared";
import { ErrorState } from "@/components/feedback/states";
import { TableSkeleton } from "@/components/ui-kit/responses-table-demo";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, ApiError } from "@/lib/api/client";
import { queryKeys, useSession } from "@/lib/api/hooks";
import type { Member } from "@/lib/api/types";
import { WorkspaceScopeEditor } from "./workspace-scope";

export function MembersPanel() {
  const t = useTranslations("admin.members");
  const tr = useTranslations("roles");
  const tc = useTranslations("common");
  const ts = useTranslations("states");
  const format = useFormatter();
  const client = useQueryClient();
  const { data: session } = useSession();
  const members = useQuery({
    queryKey: queryKeys.members,
    queryFn: () => api<Member[]>("/members"),
  });

  const update = useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Record<string, unknown>) =>
      api<Member>(`/members/${id}`, { method: "PATCH", body }),
    onSuccess: () => {
      toast.success(t("roleUpdated"));
      client.invalidateQueries({ queryKey: queryKeys.members });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : tc("errorGeneric")),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api(`/members/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast.success(t("removed"));
      client.invalidateQueries({ queryKey: queryKeys.members });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : tc("errorGeneric")),
  });

  if (members.isLoading) return <TableSkeleton rows={3} columns={5} />;
  if (members.error)
    return (
      <ErrorState
        title={ts("errorTitle")}
        description={ts("errorDescription")}
        action={
          <Button variant="outline" size="sm" onClick={() => members.refetch()}>
            {tc("retry")}
          </Button>
        }
      />
    );

  return (
    <div className="overflow-hidden rounded-xl border bg-card shadow-soft">
      <Table>
        <TableHeader className="bg-muted/50">
          <TableRow>
            <TableHead className="min-w-56">{t("name")}</TableHead>
            <TableHead>{t("role")}</TableHead>
            <TableHead>{t("scope")}</TableHead>
            <TableHead>{t("status")}</TableHead>
            <TableHead>{t("lastLogin")}</TableHead>
            <TableHead className="text-right">{tc("actions")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {members.data?.map((m) => {
            const isMe = m.user_id === session?.user.id;
            return (
              <TableRow key={m.id}>
                <TableCell>
                  <p className="font-medium">
                    {m.full_name}{" "}
                    {isMe && <span className="text-muted-foreground">{t("you")}</span>}
                  </p>
                  <p className="text-xs text-muted-foreground">{m.email}</p>
                </TableCell>
                <TableCell>
                  <Select
                    value={m.role}
                    onValueChange={(role) => update.mutate({ id: m.id, role })}
                  >
                    <SelectTrigger size="sm" className="w-44" aria-label={t("role")}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TENANT_ROLES.map((role) => (
                        <SelectItem key={role} value={role}>
                          {tr(role)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </TableCell>
                <TableCell>
                  {m.role === "ADMIN" ? (
                    <span className="text-sm text-muted-foreground">{t("allWorkspaces")}</span>
                  ) : (
                    <WorkspaceScopeEditor
                      allWorkspaces={m.all_workspaces}
                      workspaceIds={m.workspace_ids}
                      onSave={(scope) => update.mutate({ id: m.id, ...scope })}
                    />
                  )}
                </TableCell>
                <TableCell>
                  <Badge variant={m.status === "active" ? "positive" : "neutral"}>
                    {t(m.status)}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {m.last_login_at ? format.relativeTime(new Date(m.last_login_at)) : tc("never")}
                </TableCell>
                <TableCell className="text-right">
                  {!isMe && (
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="ghost" size="icon-sm" aria-label={t("remove")}>
                          <Trash2 aria-hidden />
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>
                            {t("removeTitle", { name: m.full_name })}
                          </AlertDialogTitle>
                          <AlertDialogDescription>{t("removeDescription")}</AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>{tc("cancel")}</AlertDialogCancel>
                          <AlertDialogAction
                            className="bg-destructive text-white hover:bg-destructive/90"
                            onClick={() => remove.mutate(m.id)}
                          >
                            {t("remove")}
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
