export interface DiffWord {
  text: string;
  changed: boolean;
}

const norm = (word: string): string => word.toLowerCase().replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "");

// Word-level diff by longest common subsequence: which words of the corrected sentence are new.
export function diffSentence(original: string, corrected: string): DiffWord[] {
  const a = original.split(/\s+/).filter(Boolean);
  const b = corrected.split(/\s+/).filter(Boolean);
  const lcs = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i -= 1) {
    for (let j = b.length - 1; j >= 0; j -= 1) {
      lcs[i][j] = norm(a[i]) === norm(b[j]) ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }
  const words: DiffWord[] = [];
  let i = 0;
  let j = 0;
  while (j < b.length) {
    if (i < a.length && norm(a[i]) === norm(b[j])) {
      words.push({ text: b[j], changed: false });
      i += 1;
      j += 1;
    } else if (i === a.length || lcs[i][j + 1] >= lcs[i + 1][j]) {
      words.push({ text: b[j], changed: true });
      j += 1;
    } else {
      i += 1;
    }
  }
  return words;
}
