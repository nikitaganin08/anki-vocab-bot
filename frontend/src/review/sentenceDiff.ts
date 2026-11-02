export interface DiffWord {
  text: string;
  changed: boolean;
}

export interface SentenceDiff {
  corrected: DiffWord[];
  // Runs of the learner's words that the fix replaced or dropped.
  removed: string[];
}

const norm = (word: string): string => word.toLowerCase().replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "");

// Word-level diff by longest common subsequence: which words of the corrected sentence are new,
// and which stretches of the original were replaced.
export function diffSentence(original: string, corrected: string): SentenceDiff {
  const a = original.split(/\s+/).filter(Boolean);
  const b = corrected.split(/\s+/).filter(Boolean);
  const lcs = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i -= 1) {
    for (let j = b.length - 1; j >= 0; j -= 1) {
      lcs[i][j] = norm(a[i]) === norm(b[j]) ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }
  const words: DiffWord[] = [];
  const removed: string[] = [];
  let run: string[] = [];
  const flush = (): void => {
    if (run.length) {
      removed.push(run.join(" "));
      run = [];
    }
  };
  let i = 0;
  let j = 0;
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && norm(a[i]) === norm(b[j])) {
      flush();
      words.push({ text: b[j], changed: false });
      i += 1;
      j += 1;
    } else if (j < b.length && (i === a.length || lcs[i][j + 1] >= lcs[i + 1][j])) {
      words.push({ text: b[j], changed: true });
      j += 1;
    } else {
      run.push(a[i]);
      i += 1;
    }
  }
  flush();
  return { corrected: words, removed };
}
