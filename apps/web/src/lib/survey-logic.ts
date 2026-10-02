import type { Question } from "@/lib/api/surveys";
type Rule = { all?: Rule[]; any?: Rule[]; question?: string; operator?: string; value?: unknown };
export function condition(rule: Rule | undefined, answers: Record<string, unknown>): boolean {
  if (!rule || !Object.keys(rule).length) return true;
  if (rule.all) return rule.all.every((r) => condition(r, answers));
  if (rule.any) return rule.any.some((r) => condition(r, answers));
  const actual = answers[rule.question || ""],
    expected = rule.value;
  if (actual == null) return false;
  if (rule.operator === "eq") return actual === expected;
  if (rule.operator === "ne") return actual !== expected;
  if (rule.operator === "contains")
    return Array.isArray(actual)
      ? actual.includes(expected)
      : typeof actual === "string" && typeof expected === "string" && actual.includes(expected);
  if (typeof actual !== "number" || typeof expected !== "number") return false;
  return rule.operator === "gt"
    ? actual > expected
    : rule.operator === "lt"
      ? actual < expected
      : false;
}
export function surveyPath(questions: Question[], answers: Record<string, unknown>): Question[] {
  const result: Question[] = [];
  const previous: Record<string, unknown> = {};
  let index = 0;
  while (index < questions.length) {
    const original = questions[index];
    if (!original) break;
    const logic = original.logic;
    if (!condition(logic.display_if as Rule, previous)) {
      index++;
      continue;
    }
    const q = {
      ...original,
      options: original.options.filter((o) => condition(o.display_if, previous)),
    };
    const carry = logic.carry_from;
    if (typeof carry === "string") {
      const value = previous[carry],
        selected = Array.isArray(value) ? value : [value];
      q.options = (questions.find((source) => source.code === carry)?.options || []).filter((o) =>
        selected.includes(o.value),
      );
    }
    result.push(q);
    if (original.code in answers) previous[original.code] = answers[original.code];
    let next = index + 1;
    for (const jump of (logic.jumps as { if: Rule; target: string }[]) || []) {
      if (original.code in answers && condition(jump.if, previous)) {
        next =
          jump.target === "end"
            ? questions.length
            : questions.findIndex((candidate) => candidate.code === jump.target);
        break;
      }
    }
    if (next <= index) break;
    index = next;
  }
  return result;
}
