// Hides the asked word (and its common inflections) in a hint, e.g. "genuine" in its own definition.
// Stems drop 1-2 trailing letters, so "genuine" also hides "genuinely"; short words need an exact start.
export function maskWord(text: string, word: string): string {
  const stems = word
    .split(/\s+/)
    .filter((token) => token.length >= 4)
    .map((token) => {
      const cut = token.length >= 7 ? 2 : token.length >= 5 ? 1 : 0;
      return token.slice(0, token.length - cut).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    });
  if (stems.length === 0) {
    return text;
  }
  return text.replace(new RegExp(`\\b(?:${stems.join("|")})\\w*`, "gi"), "___");
}
