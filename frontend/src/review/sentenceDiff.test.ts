import { describe, expect, it } from "vitest";

import { diffSentence } from "./sentenceDiff";

describe("diffSentence", () => {
  it("marks the replaced word and reports what it replaced", () => {
    const diff = diffSentence("it ended with a full reconstruction", "it ended in a full reconstruction.");
    expect(diff.corrected.filter((w) => w.changed).map((w) => w.text)).toEqual(["in"]);
    expect(diff.removed).toEqual(["with"]);
  });

  it("ignores case and punctuation-only differences", () => {
    const diff = diffSentence("I like it but no", "I like it, but no.");
    expect(diff.corrected.some((w) => w.changed)).toBe(false);
    expect(diff.removed).toEqual([]);
  });

  it("reports a rewritten stretch as one fragment", () => {
    const diff = diffSentence("He did a plea to me yesterday", "He made a plea to me yesterday");
    expect(diff.removed).toEqual(["did"]);
  });
});
