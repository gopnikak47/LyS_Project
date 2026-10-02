"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Building2, FolderKanban, MailPlus, Users } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CompanyPanel } from "./company-panel";
import { InvitationsPanel } from "./invitations-panel";
import { MembersPanel } from "./members-panel";
import { WorkspacesPanel } from "./workspaces-panel";

const TABS = [
  { value: "members", icon: Users, Panel: MembersPanel },
  { value: "invitations", icon: MailPlus, Panel: InvitationsPanel },
  { value: "workspaces", icon: FolderKanban, Panel: WorkspacesPanel },
  { value: "company", icon: Building2, Panel: CompanyPanel },
] as const;

export function AdminTabs() {
  const t = useTranslations("admin.tabs");
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const current = TABS.some((tab) => tab.value === params.get("tab"))
    ? (params.get("tab") as (typeof TABS)[number]["value"])
    : "members";

  return (
    <Tabs
      value={current}
      onValueChange={(value) => router.replace(`${pathname}?tab=${value}`, { scroll: false })}
      className="gap-6"
    >
      <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
        <TabsList className="h-auto w-max gap-1 rounded-xl p-1">
          {TABS.map(({ value, icon: Icon }) => (
            <TabsTrigger key={value} value={value} className="gap-2 rounded-lg px-3 py-2">
              <Icon aria-hidden />
              {t(value)}
            </TabsTrigger>
          ))}
        </TabsList>
      </div>
      {TABS.map(({ value, Panel }) => (
        <TabsContent key={value} value={value}>
          <Panel />
        </TabsContent>
      ))}
    </Tabs>
  );
}
