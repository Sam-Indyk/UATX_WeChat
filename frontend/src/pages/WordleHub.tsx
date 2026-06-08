import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../lib/api";
import { WORDLE_WORDS } from "../lib/wordle";

type Completion = {
  id: string;
  game_index: number;
  num_guesses: number;
  created_at: string;
};

/** Wordle game list. Each card links into /wordle/:gameIndex.
 *  Shows the user's best score per game (or "Not won yet"). */
export default function WordleHub() {
  const { request } = useApi();
  const [completions, setCompletions] = useState<Completion[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    request<Completion[]>("/api/wordle/me")
      .then(setCompletions)
      .catch((e) => setError(`Couldn't load your Wordle history: ${String(e)}`));
  }, [request]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!completions) return <p className="text-slate-500">Loading…</p>;

  // game_index → num_guesses
  const bestByGame = new Map<number, number>();
  for (const c of completions) bestByGame.set(c.game_index, c.num_guesses);

  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">UATX Wordle</h1>
        <p className="text-sm text-slate-600 max-w-prose">
          Twenty UATX-themed words — guess each in as few tries as possible.
          Classic Wordle rules: green = right letter, right spot; yellow =
          right letter, wrong spot; gray = not in the word. Word length varies
          per game.
        </p>
      </header>

      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {WORDLE_WORDS.map((word, idx) => {
          const best = bestByGame.get(idx);
          const won = best !== undefined;
          return (
            <li key={idx}>
              <Link
                to={`/wordle/${idx}`}
                className={`block rounded-lg border bg-white p-4 transition-colors hover:border-slate-400 hover:shadow-sm ${
                  won ? "border-emerald-200" : "border-slate-200"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold">Game {idx + 1}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {word.length} letters
                    </p>
                  </div>
                  {won ? (
                    <span className="shrink-0 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
                      Won in {best}
                    </span>
                  ) : (
                    <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                      Not yet
                    </span>
                  )}
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
