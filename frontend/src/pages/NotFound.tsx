import { Link } from "react-router-dom";
import Logo from "../components/Logo";

/** Shown when the URL doesn't match any route. Previously we just
 *  redirected to /, which silently swallowed typos and made debugging
 *  bad links harder. */
export default function NotFound() {
  return (
    <section className="max-w-md mx-auto text-center py-12 space-y-6">
      <div className="flex justify-center">
        <Logo size={80} className="text-amber-600" />
      </div>
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">404</h1>
        <p className="text-slate-600">
          We couldn't find that page. The link might be old, or the listing might
          have been taken down.
        </p>
      </div>
      <div className="flex flex-wrap gap-3 justify-center">
        <Link
          to="/"
          className="rounded-md bg-amber-600 px-4 py-2 text-white text-sm font-medium hover:bg-amber-700"
        >
          Back home
        </Link>
        <Link
          to="/listings"
          className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Browse books
        </Link>
      </div>
    </section>
  );
}
