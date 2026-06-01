import { Routes, Route, Navigate, Link, useLocation } from "react-router-dom";
import { SignedIn, SignedOut, SignIn, UserButton } from "@clerk/clerk-react";
import Home from "./pages/Home";
import Listings from "./pages/Listings";
import ListingDetail from "./pages/ListingDetail";
import NewListing from "./pages/NewListing";
import Onboarding from "./pages/Onboarding";
import Match from "./pages/Match";
import Inbox from "./pages/Inbox";
import Conversation from "./pages/Conversation";
import Classmates from "./pages/Classmates";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Nav />
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/sign-in/*" element={<SignInPage />} />
          <Route path="/onboarding" element={<RequireAuth><Onboarding /></RequireAuth>} />
          <Route path="/listings" element={<Listings />} />
          <Route path="/listings/new" element={<RequireAuth><NewListing /></RequireAuth>} />
          <Route path="/listings/:id" element={<ListingDetail />} />
          <Route path="/match" element={<RequireAuth><Match /></RequireAuth>} />
          <Route path="/classmates" element={<RequireAuth><Classmates /></RequireAuth>} />
          <Route path="/inbox" element={<RequireAuth><Inbox /></RequireAuth>} />
          <Route path="/inbox/:id" element={<RequireAuth><Conversation /></RequireAuth>} />
          <Route path="/settings" element={<RequireAuth><Settings /></RequireAuth>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function Nav() {
  return (
    <nav className="border-b border-slate-200 bg-white">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-6">
        <Link to="/" className="font-semibold tracking-tight">UATX_WeChat</Link>
        <Link to="/listings" className="text-sm text-slate-600 hover:text-slate-900">Browse</Link>
        <SignedIn>
          <Link to="/match" className="text-sm text-slate-600 hover:text-slate-900">For my courses</Link>
          <Link to="/classmates" className="text-sm text-slate-600 hover:text-slate-900">Classmates</Link>
          <Link to="/inbox" className="text-sm text-slate-600 hover:text-slate-900">Inbox</Link>
          <Link to="/listings/new" className="text-sm text-slate-600 hover:text-slate-900">Sell a book</Link>
        </SignedIn>
        <div className="ml-auto flex items-center gap-3">
          <SignedOut>
            <Link to="/sign-in" className="text-sm font-medium">Sign in</Link>
          </SignedOut>
          <SignedIn>
            <Link to="/settings" className="text-sm text-slate-600 hover:text-slate-900">Settings</Link>
            <UserButton afterSignOutUrl="/" />
          </SignedIn>
        </div>
      </div>
    </nav>
  );
}

function SignInPage() {
  return (
    <div className="flex justify-center pt-8">
      <SignIn routing="path" path="/sign-in" signUpUrl="/sign-in" afterSignInUrl="/onboarding" afterSignUpUrl="/onboarding" />
    </div>
  );
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        <Navigate to="/sign-in" replace state={{ from: location }} />
      </SignedOut>
    </>
  );
}
