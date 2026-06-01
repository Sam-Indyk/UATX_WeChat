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
import MyListings from "./pages/MyListings";
import MyListingDetail from "./pages/MyListingDetail";
import MyInquiries from "./pages/MyInquiries";
import { useUnread } from "./hooks/useUnreadCount";

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
          <Route path="/my-listings" element={<RequireAuth><MyListings /></RequireAuth>} />
          <Route path="/my-listings/:id" element={<RequireAuth><MyListingDetail /></RequireAuth>} />
          <Route path="/my-inquiries" element={<RequireAuth><MyInquiries /></RequireAuth>} />
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
          <ClassmatesLink />
          <MyListingsLink />
          <MyInquiriesLink />
          <InboxLink />
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

function InboxLink() {
  const { counts } = useUnread();
  const unread = counts.total;
  return (
    <Link to="/inbox" className="relative text-sm text-slate-600 hover:text-slate-900">
      Inbox
      {unread > 0 && (
        <span
          className="absolute -top-2 -right-3 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-semibold flex items-center justify-center"
          aria-label={`${unread} unread`}
        >
          {unread > 99 ? "99+" : unread}
        </span>
      )}
    </Link>
  );
}

function MyListingsLink() {
  // Per-context unread: how many incoming messages across listings I'm
  // selling that I haven't read yet. From PR #17's /api/me/unread-counts.
  const { counts } = useUnread();
  const unread = counts.listings;
  return (
    <Link to="/my-listings" className="relative text-sm text-slate-600 hover:text-slate-900">
      My listings
      {unread > 0 && (
        <span
          className="absolute -top-2 -right-3 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-semibold flex items-center justify-center"
          aria-label={`${unread} unread on your listings`}
        >
          {unread > 99 ? "99+" : unread}
        </span>
      )}
    </Link>
  );
}

function ClassmatesLink() {
  const { counts } = useUnread();
  const unread = counts.dms;
  return (
    <Link to="/classmates" className="relative text-sm text-slate-600 hover:text-slate-900">
      Classmates
      {unread > 0 && (
        <span
          className="absolute -top-2 -right-3 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-semibold flex items-center justify-center"
          aria-label={`${unread} unread DMs`}
        >
          {unread > 99 ? "99+" : unread}
        </span>
      )}
    </Link>
  );
}

function MyInquiriesLink() {
  const { counts } = useUnread();
  const unread = counts.inquiries;
  return (
    <Link to="/my-inquiries" className="relative text-sm text-slate-600 hover:text-slate-900">
      My inquiries
      {unread > 0 && (
        <span
          className="absolute -top-2 -right-3 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-semibold flex items-center justify-center"
          aria-label={`${unread} unread on your inquiries`}
        >
          {unread > 99 ? "99+" : unread}
        </span>
      )}
    </Link>
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
