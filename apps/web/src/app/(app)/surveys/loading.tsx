import { Skeleton } from "@/components/ui/skeleton";
import { SurveyCardSkeleton } from "@/components/surveys/survey-card";

export default function SurveysLoading() {
  return (
    <div className="space-y-6" aria-busy="true">
      <div className="space-y-2">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      <Skeleton className="h-10 w-full" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <SurveyCardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}
