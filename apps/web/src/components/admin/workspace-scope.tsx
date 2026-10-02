"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useWorkspaces } from "@/lib/api/hooks";

type Scope = { all_workspaces: boolean; workspace_ids: string[] };

/** Chọn phạm vi workspace: tất cả hoặc một số workspace cụ thể. */
export function WorkspaceScopePicker({
  value,
  onChange,
}: {
  value: Scope;
  onChange: (scope: Scope) => void;
}) {
  const t = useTranslations("admin.members");
  const { data: workspaces = [] } = useWorkspaces();
  return (
    <div className="space-y-3">
      <RadioGroup
        value={value.all_workspaces ? "all" : "some"}
        onValueChange={(v) => onChange({ ...value, all_workspaces: v === "all" })}
      >
        <div className="flex items-center gap-2">
          <RadioGroupItem id="scope-all" value="all" />
          <Label htmlFor="scope-all">{t("scopeAll")}</Label>
        </div>
        <div className="flex items-center gap-2">
          <RadioGroupItem id="scope-some" value="some" />
          <Label htmlFor="scope-some">{t("scopeSome")}</Label>
        </div>
      </RadioGroup>
      {!value.all_workspaces && (
        <ul className="max-h-56 space-y-2 overflow-y-auto rounded-lg border p-3">
          {workspaces.map((ws) => {
            const checked = value.workspace_ids.includes(ws.id);
            return (
              <li key={ws.id} className="flex items-center gap-2">
                <Checkbox
                  id={`ws-${ws.id}`}
                  checked={checked}
                  onCheckedChange={(c) =>
                    onChange({
                      ...value,
                      workspace_ids: c
                        ? [...value.workspace_ids, ws.id]
                        : value.workspace_ids.filter((id) => id !== ws.id),
                    })
                  }
                />
                <Label htmlFor={`ws-${ws.id}`} className="font-normal">
                  {ws.name}
                </Label>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function WorkspaceScopeEditor({
  allWorkspaces,
  workspaceIds,
  onSave,
}: {
  allWorkspaces: boolean;
  workspaceIds: string[];
  onSave: (scope: Scope) => void;
}) {
  const t = useTranslations("admin.members");
  const tc = useTranslations("common");
  const [open, setOpen] = useState(false);
  const [scope, setScope] = useState<Scope>({
    all_workspaces: allWorkspaces,
    workspace_ids: workspaceIds,
  });
  const label = allWorkspaces
    ? t("allWorkspaces")
    : t("someWorkspaces", { count: workspaceIds.length });

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) setScope({ all_workspaces: allWorkspaces, workspace_ids: workspaceIds });
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1">
          {label}
          <ChevronDown aria-hidden />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("scopeTitle")}</DialogTitle>
          <DialogDescription>{label}</DialogDescription>
        </DialogHeader>
        <WorkspaceScopePicker value={scope} onChange={setScope} />
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            {tc("cancel")}
          </Button>
          <Button
            onClick={() => {
              onSave(scope);
              setOpen(false);
            }}
          >
            {tc("save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
