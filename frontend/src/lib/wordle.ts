/** UATX-flavored word list. Each entry is its own "game", indexed by
 *  position in this array — the hub page renders them as Game 1..N.
 *
 *  All words are stored lowercase; the gameplay is case-insensitive.
 *  Backend just persists (user, game_index, num_guesses) — it has no
 *  knowledge of the words themselves, so adding words here doesn't
 *  require a migration.
 */
export const WORDLE_WORDS: string[] = [
  "palantir",
  "neoplatonism",
  "lonsdale",
  "ferguson",
  "polaris",
  "talentnetwork",
  "aristotle",
  "esoteric",
  "teleology",
  "claude",
  "ontological",
  "kantian",
  "macmini",
  "straussian",
  "eschatology",
  "scooter",
  "polity",
  "phil",
  "carlos",
  "crocker",
];

/** Number of guesses for a given word length. Classic Wordle is 6
 *  guesses for a 5-letter word; longer words get more room. */
export function guessesAllowed(word: string): number {
  return Math.max(6, word.length);
}

export type LetterStatus = "correct" | "present" | "absent";

/** Wordle coloring rules with duplicate-letter handling.
 *
 *  Two passes:
 *  1. Greens: mark every position where guess[i] === answer[i].
 *  2. Yellows: for remaining unmatched guess letters, mark "present"
 *     only if there's still an unmatched answer letter equal to it.
 *     This prevents "EEEEE" against "EERIE" from showing five greens.
 */
export function scoreGuess(guess: string, answer: string): LetterStatus[] {
  const g = guess.toLowerCase();
  const a = answer.toLowerCase();
  const result: LetterStatus[] = new Array(g.length).fill("absent");
  // Remaining unmatched answer letters (after greens removed).
  const remaining: Record<string, number> = {};

  for (let i = 0; i < g.length; i++) {
    if (g[i] === a[i]) {
      result[i] = "correct";
    } else {
      remaining[a[i]] = (remaining[a[i]] ?? 0) + 1;
    }
  }

  for (let i = 0; i < g.length; i++) {
    if (result[i] === "correct") continue;
    const letter = g[i];
    if ((remaining[letter] ?? 0) > 0) {
      result[i] = "present";
      remaining[letter] -= 1;
    }
  }

  return result;
}
