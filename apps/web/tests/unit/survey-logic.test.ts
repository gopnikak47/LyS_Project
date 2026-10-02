import { describe, expect, it } from "vitest";
import type { Question } from "@/lib/api/surveys";
import { condition, surveyPath } from "@/lib/survey-logic";

const q = (code: string, logic: Question["logic"] = {}): Question => ({
  id: code,
  code,
  type: "single_choice",
  title: { vi: code },
  description: {},
  required: true,
  config: {},
  logic,
  options: [
    { value: "a", label: { vi: "A" } },
    { value: "b", label: { vi: "B" } },
  ],
});

describe("survey path", () => {
  it("combines AND/OR and handles malformed contains safely", () => {
    expect(
      condition(
        {
          all: [
            { question: "score", operator: "lt", value: 3 },
            { any: [{ question: "tag", operator: "contains", value: "late" }] },
          ],
        },
        { score: 1, tag: ["late"] },
      ),
    ).toBe(true);
    expect(condition({ question: "tag", operator: "contains", value: {} }, { tag: "abc" })).toBe(
      false,
    );
  });
  it("hides downstream required questions and jumps only forward", () => {
    const questions = [
      q("first", {
        jumps: [{ if: { question: "first", operator: "eq", value: "a" }, target: "last" }],
      }),
      q("skip"),
      q("last"),
    ];
    expect(surveyPath(questions, { first: "a" }).map((x) => x.code)).toEqual(["first", "last"]);
    expect(surveyPath([q("x", { jumps: [{ if: {}, target: "x" }] })], { x: "a" })).toHaveLength(1);
  });
  it("carries selected options without mutating the survey", () => {
    const questions = [q("first"), q("next", { carry_from: "first" })];
    expect(surveyPath(questions, { first: "b" })[1]?.options.map((x) => x.value)).toEqual(["b"]);
    expect(questions[1]?.options).toHaveLength(2);
  });
});
