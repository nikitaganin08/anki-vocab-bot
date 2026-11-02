import { describe, expect, it } from "vitest";

import { diffSentence } from "./sentenceDiff";

const changed = (a: string, b: string): string[] =>
  diffSentence(a, b)
    .filter((w) => w.changed)
    .map((w) => w.text);

describe("diffSentence", () => {
  it("marks the replaced word", () => {
    expect(changed("it ended with a full reconstruction", "it ended in a full reconstruction.")).toEqual(["in"]);
  });

  it("ignores case and punctuation-only differences", () => {
    expect(changed("I like it but no", "I like it, but no.")).toEqual([]);
  });

  it("marks inserted words", () => {
    expect(changed("He did a plea to me", "He made a plea to me")).toEqual(["made"]);
  });
});
