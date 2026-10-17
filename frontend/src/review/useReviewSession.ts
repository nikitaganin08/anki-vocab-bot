import { useEffect, useRef, useState } from "react";

import { ApiError, checkAnswer, getReviewSession, getReviewSummary, gradeCard } from "../api/client";
import type { CheckResponse, ReviewSessionItem, ReviewSummary } from "../api/types";
import type { ReviewMode } from "../home/HomeView";

export const ROUND_SIZE = 10;

export interface CheckedAnswer {
  typed: string;
  hintUsed: boolean;
  responseMs: number;
  result: CheckResponse;
}

export interface Round {
  number: number;
  // Session items; "Запомнил" on an intro inserts a typed copy of it.
  queue: ReviewSessionItem[];
  pos: number;
  // Typed questions in the round: each intro yields exactly one, so the denominator never grows.
  total: number;
  graded: number;
}

type StoredPhase = "loading" | "error" | "item" | "answer" | "roundEnd" | "done";
export type ReviewPhase = Exclude<StoredPhase, "item"> | "intro" | "question";

interface State {
  phase: StoredPhase;
  round: Round;
  answer: CheckedAnswer | null;
  summary: ReviewSummary | null;
  next: ReviewSessionItem[];
  error: unknown;
  busy: boolean;
}

function newRound(number: number, queue: ReviewSessionItem[]): Round {
  return { number, queue, pos: 0, total: queue.length, graded: 0 };
}

export function useReviewSession(mode: ReviewMode) {
  const [state, setState] = useState<State>({
    phase: "loading",
    round: newRound(1, []),
    answer: null,
    summary: null,
    next: [],
    error: null,
    busy: false,
  });
  const gradedTotal = useRef(0);
  const shownAt = useRef(0);
  const item = state.round.queue[state.round.pos];

  // Every round boundary refreshes the summary too, so minutes and goal progress stay current.
  // An empty round means nothing is left today (limits may have been hit since the dashboard).
  async function fetchRound(onItems: (items: ReviewSessionItem[]) => Partial<State>): Promise<void> {
    setState((s) => ({ ...s, phase: "loading", busy: false }));
    // A capped session asks only for what is left of the cap, so the round (and its "k из T")
    // ends at the cap; once the cap is reached, further rounds are regular ones.
    const capLeft = (mode.capCards ?? 0) - gradedTotal.current;
    const size = capLeft > 0 ? Math.min(ROUND_SIZE, capLeft) : ROUND_SIZE;
    try {
      const [items, summary] = await Promise.all([
        getReviewSession({ size, includeBacklog: mode.includeBacklog ?? false }),
        getReviewSummary(),
      ]);
      setState((s) => ({
        ...s,
        summary,
        answer: null,
        ...(items.length === 0 ? { phase: "done" } : onItems(items)),
      }));
    } catch (error) {
      setState((s) => ({ ...s, phase: "error", error }));
    }
  }

  const loadRound = (number: number): Promise<void> =>
    fetchRound((items) => ({ phase: "item", round: newRound(number, items) }));

  useEffect(() => {
    void loadRound(1);
  }, []);

  useEffect(() => {
    if (state.phase === "item" && !item.intro) {
      shownAt.current = Date.now();
    }
  }, [state.phase, item]);

  function fail(error: unknown): void {
    setState((s) => ({ ...s, phase: "error", error, busy: false }));
  }

  function remember(): void {
    setState((s) => {
      const queue = [...s.round.queue];
      queue.splice(s.round.pos + 2, 0, { ...queue[s.round.pos], intro: false });
      return { ...s, round: { ...s.round, queue, pos: s.round.pos + 1 } };
    });
  }

  async function check(typed: string, hintUsed: boolean): Promise<void> {
    const responseMs = Date.now() - shownAt.current;
    setState((s) => ({ ...s, busy: true }));
    try {
      const result = await checkAnswer(item.card.id, {
        typed,
        prompt_kind: item.prompt.kind,
        prompt_index: item.prompt.index,
        hint_used: hintUsed,
      });
      setState((s) => ({ ...s, phase: "answer", answer: { typed, hintUsed, responseMs, result }, busy: false }));
    } catch (error) {
      fail(error);
    }
  }

  async function grade(rating: number, overridden = false): Promise<void> {
    const answer = state.answer;
    if (answer === null) {
      return;
    }
    setState((s) => ({ ...s, busy: true }));
    try {
      await gradeCard(item.card.id, {
        rating,
        auto_rating: answer.result.auto_rating,
        overridden,
        typed: answer.typed,
        prompt_kind: item.prompt.kind,
        prompt_index: item.prompt.index,
        verdict: answer.result.verdict,
        hint_used: answer.hintUsed,
        response_ms: answer.responseMs,
        // Echo the server string as-is: a Date round-trip would drop microseconds.
        expected_due_at: item.srs_due_at,
      });
    } catch (error) {
      // 409: double tap or a stale round; the server already moved on, so take a fresh round.
      if (error instanceof ApiError && error.status === 409) {
        return loadRound(state.round.number);
      }
      return fail(error);
    }

    gradedTotal.current += 1;
    if (gradedTotal.current === mode.capCards || state.round.pos + 1 >= state.round.queue.length) {
      return fetchRound((items) => ({ phase: "roundEnd", next: items }));
    }
    setState((s) => ({
      ...s,
      phase: "item",
      answer: null,
      busy: false,
      round: { ...s.round, pos: s.round.pos + 1, graded: s.round.graded + 1 },
    }));
  }

  function nextRound(): void {
    setState((s) => ({ ...s, phase: "item", round: newRound(s.round.number + 1, s.next), next: [] }));
  }

  const phase: ReviewPhase =
    state.phase === "item" ? (item.intro ? "intro" : "question") : state.phase;

  return {
    phase,
    item,
    round: state.round,
    answer: state.answer,
    summary: state.summary,
    error: state.error,
    busy: state.busy,
    remember,
    check,
    grade,
    nextRound,
    retry: () => void loadRound(state.round.number),
  };
}
