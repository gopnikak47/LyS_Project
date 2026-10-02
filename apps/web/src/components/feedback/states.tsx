import type { LucideIcon } from "lucide-react";
import { Construction, Inbox, TriangleAlert } from "lucide-react";
import { cn } from "@/lib/utils";

type StateProps = {
  title: string;
  description?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
  className?: string;
};

function StateBlock({
  title,
  description,
  icon: Icon,
  action,
  className,
  tone,
  role,
}: StateProps & { icon: LucideIcon; tone: string; role?: "alert" | "status" }) {
  return (
    <div
      role={role}
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed bg-card px-6 py-12 text-center",
        className,
      )}
    >
      <span className={cn("grid size-12 place-items-center rounded-full", tone)}>
        <Icon className="size-6" aria-hidden />
      </span>
      <div className="max-w-sm space-y-1">
        <p className="font-semibold">{title}</p>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  );
}

/** Trạng thái rỗng: dùng cho mọi bảng/biểu đồ chưa có dữ liệu. */
export function EmptyState({ icon = Inbox, ...props }: StateProps) {
  return <StateBlock {...props} icon={icon} tone="bg-muted text-muted-foreground" role="status" />;
}

/** Trạng thái lỗi: không hiển thị chi tiết kỹ thuật, luôn có hành động thử lại. */
export function ErrorState({ icon = TriangleAlert, ...props }: StateProps) {
  return (
    <StateBlock {...props} icon={icon} tone="bg-negative-soft text-negative-ink" role="alert" />
  );
}

export function ComingSoonState({ icon = Construction, ...props }: StateProps) {
  return <StateBlock {...props} icon={icon} tone="bg-primary-soft text-primary" />;
}
