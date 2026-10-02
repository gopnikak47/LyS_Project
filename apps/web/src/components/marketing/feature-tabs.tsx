import { getTranslations } from "next-intl/server";
import {
  BrainCircuit,
  CircleCheck,
  GitBranch,
  ListChecks,
  Palette,
  SlidersHorizontal,
} from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const FEATURES = [
  { key: "design", icon: Palette },
  { key: "questionTypes", icon: ListChecks },
  { key: "settings", icon: SlidersHorizontal },
  { key: "logic", icon: GitBranch },
  { key: "nlp", icon: BrainCircuit },
] as const;

export async function FeatureTabs() {
  const t = await getTranslations("marketing.features");

  return (
    <Tabs defaultValue="design" className="gap-8">
      <div className="-mx-4 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex sm:justify-center-safe sm:px-0">
        <TabsList className="h-auto w-max gap-1 rounded-xl p-1">
          {FEATURES.map(({ key, icon: Icon }) => (
            <TabsTrigger
              key={key}
              value={key}
              className="gap-2 rounded-lg px-3 py-2 text-sm sm:px-4"
            >
              <Icon aria-hidden />
              {t(`${key}.label`)}
            </TabsTrigger>
          ))}
        </TabsList>
      </div>
      {FEATURES.map(({ key, icon: Icon }) => (
        <TabsContent key={key} value={key}>
          <div className="grid items-center gap-8 rounded-2xl border bg-card p-6 shadow-soft sm:p-10 lg:grid-cols-2">
            <div className="space-y-4">
              <h3 className="text-2xl font-semibold tracking-tight">{t(`${key}.title`)}</h3>
              <p className="text-muted-foreground">{t(`${key}.description`)}</p>
              <ul className="space-y-3">
                {(["point1", "point2", "point3"] as const).map((point) => (
                  <li key={point} className="flex items-start gap-3">
                    <CircleCheck className="mt-0.5 size-5 shrink-0 text-positive" aria-hidden />
                    <span>{t(`${key}.${point}`)}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div
              aria-hidden
              className="grid aspect-[4/3] place-items-center rounded-xl bg-gradient-to-br from-primary-soft via-background to-accent"
            >
              <span className="grid size-24 place-items-center rounded-3xl bg-card shadow-soft">
                <Icon className="size-10 text-primary" />
              </span>
            </div>
          </div>
        </TabsContent>
      ))}
    </Tabs>
  );
}
