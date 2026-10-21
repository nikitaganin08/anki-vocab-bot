import type { EntryType } from "./api/types";

export const ENTRY_TYPES: { value: EntryType; label: string; description: string; example: string }[] = [
  { value: "word", label: "Word", description: "A single word", example: "reluctant" },
  {
    value: "phrasal_verb",
    label: "Phrasal verb",
    description: "A verb plus a particle; the meaning changes",
    example: "give up",
  },
  {
    value: "collocation",
    label: "Collocation",
    description: "Words that usually go together, including verb plus preposition",
    example: "make a decision, depend on",
  },
  {
    value: "idiom",
    label: "Idiom",
    description: "The meaning does not follow from the words",
    example: "kick the bucket",
  },
  { value: "proverb", label: "Proverb", description: "A proverb or saying", example: "better late than never" },
  {
    value: "expression",
    label: "Phrase",
    description: "Any other stable phrase: linking phrases, fixed pairs",
    example: "by the way, back and forth",
  },
];

export function entryTypeLabel(type: EntryType): string {
  return ENTRY_TYPES.find((t) => t.value === type)?.label ?? type;
}
