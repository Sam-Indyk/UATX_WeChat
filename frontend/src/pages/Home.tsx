import { Link } from "react-router-dom";
import { SignedIn, SignedOut } from "@clerk/clerk-react";
import Logo from "../components/Logo";

export default function Home() {
  return (
    <div className="space-y-12 sm:space-y-16 py-6 sm:py-12">
      {/* Hero */}
      <section className="text-center space-y-6 max-w-2xl mx-auto">
        <div className="flex justify-center">
          <Logo size={96} className="text-amber-600" />
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 leading-tight">
          Your marketplace for buying and selling books and everything else!
        </h1>
        <SignedOut>
          <Link
            to="/sign-in"
            className="inline-block rounded-lg bg-amber-600 px-6 py-3 text-white text-base font-semibold hover:bg-amber-700 shadow-sm"
          >
            Sign in with your UATX Google Account
          </Link>
        </SignedOut>
        <SignedIn>
          <div className="flex flex-wrap gap-3 justify-center">
            <Link
              to="/feedback"
              className="rounded-lg bg-amber-600 px-6 py-3 text-white text-base font-semibold hover:bg-amber-700 shadow-sm"
            >
              Got an idea?
            </Link>
            <Link
              to="/match"
              className="rounded-lg bg-amber-600 px-6 py-3 text-white text-base font-semibold hover:bg-amber-700 shadow-sm"
            >
              See books for my courses
            </Link>
            <Link
              to="/listings"
              className="rounded-lg bg-amber-600 px-6 py-3 text-white text-base font-semibold hover:bg-amber-700 shadow-sm"
            >
              Browse all listings
            </Link>
          </div>
        </SignedIn>
      </section>

      {/* Feature highlights */}
      <section className="grid gap-4 sm:grid-cols-3 max-w-4xl mx-auto">
        <FeatureCard
          title="Matched to your courses"
          body="List the classes you're in, and we surface listings from students who took those same courses. Sorted by who took them most recently."
        />
        <FeatureCard
          title="Live chat"
          body="Message sellers in the app and arrange the handoff. Threads update live."
        />
        <FeatureCard
          title="More than textbooks"
          body="Check out 'Everything else' to see non-books! Some of the posts and kinda silly."
        />
      </section>

      {/* Project credit footnote */}
      <p className="text-center text-xs text-slate-400">
        Built for UATX students by UATX student Samuel Indyk and Eitan Zarin. SWE Final Project Spring 2026.
      </p>
    </div>
  );
}

function FeatureCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 space-y-1.5 hover:border-slate-300 transition-colors">
      <h2 className="font-semibold text-slate-900">{title}</h2>
      <p className="text-sm text-slate-600 leading-relaxed">{body}</p>
    </div>
  );
}
