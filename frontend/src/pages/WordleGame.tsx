import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useApi } from "../lib/api";
import { WORDLE_WORDS, guessesAllowed, scoreGuess } from "../lib/wordle";
import type { LetterStatus } from "../lib/wordle";

type GameStatus = "playing" | "won" | "lost";

const CELL_STYLES: Record<LetterStatus, string> = {
  correct: "bg-emerald-500 text-white border-emerald-500",
  present: "bg-amber-400 text-white border-amber-400",
  absent: "bg-slate-300 text-slate-800 border-slate-300",
};

/** A single Wordle game. URL: /wordle/:gameIndex. Reads the word from
 *  the frontend word list, runs all gameplay locally, POSTs a win to
 *  the backend on success. */
export default function WordleGame() {
  const { gameIndex } = useParams();
  const { request } = useApi();

  const idx = parseInt(gameIndex ?? "", 10);
  const word = Number.isFinite(idx) ? WORDLE_WORDS[idx] : undefined;

  const [guesses, setGuesses] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<GameStatus>("playing");
  const [error, setError] = useState<string | null>(null);

  const maxGuesses = useMemo(
    () => (word ? guessesAllowed(word) : 0),
    [word],
  );

  // Reset on game-index change (browser back/forward, or hub re-entry).
  useEffect(() => {
    setGuesses([]);
    setInput("");
    setStatus("playing");
    setError(null);
  }, [idx]);

  // Score every committed guess once and memoize. Cheap, but keeps the
  // render loop tidy.
  const scoredHistory = useMemo(() => {
    if (!word) return [];
    return guesses.map((g) => ({
      guess: g,
      scores: scoreGuess(g, word),
    }));
  }, [guesses, word]);

  if (!word) {
    return (
      <section className="space-y-3">
        <p className="text-red-600">No such game.</p>
        <Link to="/wordle" className="text-sm underline text-slate-600">
          ← Back to game list
        </Link>
      </section>
    );
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    if (status !== "playing") return;
    const cleaned = input.toLowerCase().replace(/[^a-z]/g, "");
    if (cleaned.length !== word!.length) {
      setError(`Guess must be exactly ${word!.length} letters.`);
      return;
    }
    setError(null);
    const nextGuesses = [...guesses, cleaned];
    setGuesses(nextGuesses);
    setInput("");

    if (cleaned === word!.toLowerCase()) {
      setStatus("won");
      // Fire-and-forget: record the win. If the request fails (network),
      // the user still sees the win locally; we just won't sync this
      // attempt to their history.
      request("/api/wordle/complete", {
        method: "POST",
        body: { game_index: idx, num_guesses: nextGuesses.length },
      }).catch(() => {});
    } else if (nextGuesses.length >= maxGuesses) {
      setStatus("lost");
    }
  }

  function reset() {
    setGuesses([]);
    setInput("");
    setStatus("playing");
    setError(null);
  }

  return (
    <section className="space-y-6 max-w-md">
      <header className="space-y-1">
        <Link to="/wordle" className="text-sm text-slate-600 hover:text-slate-900">
          ← All games
        </Link>
        <h1 className="text-2xl font-semibold">Game {idx + 1}</h1>
        <p className="text-xs text-slate-500">
          {word.length} letters · up to {maxGuesses} guesses
        </p>
      </header>

      {/* Guess history grid */}
      <div className="space-y-1.5">
        {scoredHistory.map(({ guess, scores }, rowIdx) => (
          <Row key={rowIdx} length={word.length}>
            {Array.from({ length: word.length }, (_, i) => (
              <Cell key={i} status={scores[i]} letter={guess[i]} />
            ))}
          </Row>
        ))}
        {/* Pending current guess row (visual echo of the input box) */}
        {status === "playing" && (
          <Row length={word.length}>
            {Array.from({ length: word.length }, (_, i) => (
              <Cell key={i} letter={input[i]} />
            ))}
          </Row>
        )}
        {/* Empty future rows so the board has consistent height */}
        {Array.from(
          {
            length: Math.max(
              0,
              maxGuesses - guesses.length - (status === "playing" ? 1 : 0),
            ),
          },
          (_, i) => (
            <Row key={`empty-${i}`} length={word.length}>
              {Array.from({ length: word.length }, (_, j) => (
                <Cell key={j} />
              ))}
            </Row>
          ),
        )}
      </div>

      {status === "playing" && (
        <form onSubmit={submit} className="space-y-2">
          <input
            value={input}
            onChange={(e) =>
              setInput(e.target.value.toLowerCase().replace(/[^a-z]/g, "").slice(0, word.length))
            }
            placeholder={`Type a ${word.length}-letter guess…`}
            autoFocus
            spellCheck={false}
            autoComplete="off"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-base tracking-widest uppercase"
            maxLength={word.length}
          />
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={input.length !== word.length}
            className="rounded-md bg-amber-600 px-4 py-2 text-white text-sm font-medium hover:bg-amber-700 disabled:opacity-50"
          >
            Guess
          </button>
        </form>
      )}

      {status === "won" && (
        <div className="space-y-2 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3">
          <p className="text-emerald-800 font-semibold">
            Got it in {guesses.length}! 🎉
          </p>
          <p className="text-sm text-emerald-700">
            The word was{" "}
            <span className="font-semibold uppercase tracking-wider">{word}</span>.
          </p>
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={reset}
              className="rounded-md border border-emerald-300 bg-white px-3 py-1.5 text-xs font-medium text-emerald-800 hover:bg-emerald-50"
            >
              Play again
            </button>
            <Link
              to="/wordle"
              className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700"
            >
              Pick another game
            </Link>
          </div>
        </div>
      )}

      {status === "lost" && (
        <div className="space-y-2 rounded-md border border-slate-200 bg-slate-50 px-4 py-3">
          <p className="text-slate-800 font-semibold">Out of guesses.</p>
          <p className="text-sm text-slate-700">
            The word was{" "}
            <span className="font-semibold uppercase tracking-wider">{word}</span>.
          </p>
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={reset}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
            >
              Try again
            </button>
            <Link
              to="/wordle"
              className="rounded-md bg-slate-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800"
            >
              Pick another game
            </Link>
          </div>
        </div>
      )}
    </section>
  );
}

function Row({ length, children }: { length: number; children: React.ReactNode }) {
  return (
    <div
      className="grid gap-1.5"
      style={{ gridTemplateColumns: `repeat(${length}, minmax(0, 1fr))` }}
    >
      {children}
    </div>
  );
}

function Cell({
  letter,
  status,
}: {
  letter?: string;
  status?: LetterStatus;
}) {
  const base =
    "aspect-square flex items-center justify-center rounded border text-lg font-bold uppercase";
  const colored = status
    ? CELL_STYLES[status]
    : letter
      ? "bg-white border-slate-400 text-slate-900"
      : "bg-white border-slate-200 text-slate-300";
  return <div className={`${base} ${colored}`}>{letter ?? ""}</div>;
}
