import { Link } from "react-router-dom";
import { SignedIn, SignedOut } from "@clerk/clerk-react";

export default function Home() {
  return (
    <section className="space-y-6 py-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">UATX_WeChat</h1>
        <p className="mt-2 text-slate-600 max-w-prose">
          Buy and sell used textbooks with other UATX students. We match you with sellers
          who took the same courses you're in now, so you find the right edition fast.
        </p>
      </header>

      <SignedOut>
        <Link
          to="/sign-in"
          className="inline-block rounded-md bg-slate-900 px-4 py-2 text-white text-sm font-medium hover:bg-slate-800"
        >
          Sign in with your UATX Google
        </Link>
      </SignedOut>
      <SignedIn>
        <div className="flex flex-wrap gap-3">
          <Link
            to="/match"
            className="inline-block rounded-md bg-slate-900 px-4 py-2 text-white text-sm font-medium hover:bg-slate-800"
          >
            See books for my courses
          </Link>
          <Link
            to="/listings"
            className="inline-block rounded-md border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-100"
          >
            Browse all listings
          </Link>
        </div>
      </SignedIn>
    </section>
  );
}
