import { useEffect, useState } from "react";
import { Routes, Route, Navigate, Link, useLocation } from "react-router-dom";
import { SignedIn, SignedOut, SignIn, UserButton } from "@clerk/clerk-react";
import Home from "./pages/Home";
import Listings from "./pages/Listings";
import ListingDetail from "./pages/ListingDetail";
import NewListing from "./pages/NewListing";
import MyClasses from "./pages/MyClasses";
import Match from "./pages/Match";
import Conversation from "./pages/Conversation";
import Classmates from "./pages/Classmates";
import Settings from "./pages/Settings";
import MyListings from "./pages/MyListings";
import MyListingDetail from "./pages/MyListingDetail";
import MyInquiries from "./pages/MyInquiries";
import EverythingElse from "./pages/EverythingElse";
import NewItem from "./pages/NewItem";
import UserProfile from "./pages/UserProfile";
import Feedback from "./pages/Feedback";
import NotFound from "./pages/NotFound";
import Logo from "./components/Logo";
import { useUnread } from "./hooks/useUnreadCount";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Nav />
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/sign-in/*" element={<SignInPage />} />
          <Route path="/my-classes" element={<RequireAuth><MyClasses /></RequireAuth>} />
          {/* Back-compat: Clerk's afterSignInUrl used to point here and some
              older docs/links reference /onboarding. Redirect so nothing 404s. */}
          <Route path="/onboarding" element={<Navigate to="/my-classes" replace />} />
          <Route path="/listings" element={<Listings />} />
          <Route path="/listings/new" element={<RequireAuth><NewListing /></RequireAuth>} />
          <Route path="/listings/:id" element={<ListingDetail />} />
          <Route path="/match" element={<RequireAuth><Match /></RequireAuth>} />
          <Route path="/classmates" element={<RequireAuth><Classmates /></RequireAuth>} />
          {/* /inbox top-level was removed in PR #21 — listing chats live
              in /my-listings (seller) and /my-inquiries (buyer); DMs in
              /classmates. /inbox/:id stays as back-compat for old links. */}
          <Route path="/inbox/:id" element={<RequireAuth><Conversation /></RequireAuth>} />
          <Route path="/my-listings" element={<RequireAuth><MyListings /></RequireAuth>} />
          <Route path="/my-listings/:id" element={<RequireAuth><MyListingDetail /></RequireAuth>} />
          <Route path="/my-inquiries" element={<RequireAuth><MyInquiries /></RequireAuth>} />
          <Route path="/everything-else" element={<EverythingElse />} />
          <Route path="/everything-else/new" element={<RequireAuth><NewItem /></RequireAuth>} />
          <Route path="/settings" element={<RequireAuth><Settings /></RequireAuth>} />
          <Route path="/users/:userId" element={<RequireAuth><UserProfile /></RequireAuth>} />
          <Route path="/feedback" element={<RequireAuth><Feedback /></RequireAuth>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  );
}

/** Top nav. Horizontal at >=md, hamburger + slide-down menu below. The
 *  signed-in nav has six links plus the user controls — too many to fit
 *  on a phone, so on mobile we collapse everything except the brand and
 *  the user button into a menu trigger. */
function Nav() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const close = () => setOpen(false);

  // Auto-close the mobile menu on any route change.
  useEffect(() => {
    setOpen(false);
  }, [location.pathname, location.search]);

  return (
    <nav className="border-b border-slate-200 bg-white">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-6">
        <Link to="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <Logo size={28} className="text-amber-600 shrink-0" />
          <span>UATX_WeChat</span>
        </Link>

        {/* Desktop links — hidden below md. whitespace-nowrap keeps multi-
            word labels on one line; without it flex shrinking would wrap
            "My classes" / "For my courses" / etc. across two lines. */}
        <Link to="/listings" className="hidden md:inline whitespace-nowrap text-sm text-slate-600 hover:text-slate-900">Books</Link>
        <Link to="/everything-else" className="hidden md:inline whitespace-nowrap text-sm text-slate-600 hover:text-slate-900">Everything else</Link>
        <SignedIn>
          <Link to="/my-classes" className="hidden md:inline whitespace-nowrap text-sm text-slate-600 hover:text-slate-900">My classes</Link>
          <Link to="/match" className="hidden md:inline whitespace-nowrap text-sm text-slate-600 hover:text-slate-900">For my courses</Link>
          <ClassmatesLink mobile={false} />
          <MyListingsLink mobile={false} />
          <MyInquiriesLink mobile={false} />
        </SignedIn>

        <div className="ml-auto flex items-center gap-3">
          <SignedOut>
            <Link to="/sign-in" className="text-sm font-medium">Sign in</Link>
          </SignedOut>
          <SignedIn>
            <Link to="/settings" className="hidden md:inline whitespace-nowrap text-sm text-slate-600 hover:text-slate-900">Settings</Link>
            <UserButton afterSignOutUrl="/" />
          </SignedIn>

          {/* Hamburger — only below md. */}
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            className="md:hidden inline-flex items-center justify-center w-11 h-11 -mr-2 rounded-md text-slate-700 hover:bg-slate-100"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              {open ? (
                <>
                  <line x1="6" y1="6" x2="18" y2="18" />
                  <line x1="6" y1="18" x2="18" y2="6" />
                </>
              ) : (
                <>
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <line x1="3" y1="12" x2="21" y2="12" />
                  <line x1="3" y1="18" x2="21" y2="18" />
                </>
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile slide-down menu — only below md. */}
      {open && (
        <div className="md:hidden border-t border-slate-200 bg-white">
          <div className="max-w-5xl mx-auto px-4 py-2 flex flex-col">
            <MobileLink to="/listings" onClick={close}>Books</MobileLink>
            <MobileLink to="/everything-else" onClick={close}>Everything else</MobileLink>
            <SignedIn>
              <MobileLink to="/my-classes" onClick={close}>My classes</MobileLink>
              <MobileLink to="/match" onClick={close}>For my courses</MobileLink>
              <ClassmatesLink mobile onClick={close} />
              <MyListingsLink mobile onClick={close} />
              <MyInquiriesLink mobile onClick={close} />
              <hr className="my-1 border-slate-100" />
              <MobileLink to="/settings" onClick={close}>Settings</MobileLink>
            </SignedIn>
            <SignedOut>
              <MobileLink to="/sign-in" onClick={close}>Sign in</MobileLink>
            </SignedOut>
          </div>
        </div>
      )}
    </nav>
  );
}

function MobileLink({
  to,
  onClick,
  children,
  badge,
}: {
  to: string;
  onClick: () => void;
  children: React.ReactNode;
  badge?: number;
}) {
  return (
    <Link
      to={to}
      onClick={onClick}
      className="flex items-center justify-between px-2 py-3 text-base text-slate-700 hover:bg-slate-50 rounded-md min-h-[44px]"
    >
      <span>{children}</span>
      {badge != null && badge > 0 && (
        <span
          className="min-w-[20px] h-5 px-1.5 rounded-full bg-red-500 text-white text-xs font-semibold flex items-center justify-center"
          aria-label={`${badge} unread`}
        >
          {badge > 99 ? "99+" : badge}
        </span>
      )}
    </Link>
  );
}

/** Shared shell for the three nav links that carry an unread badge. The
 *  badge styling differs between desktop (absolute-positioned chip beside
 *  the link text) and mobile (inline-aligned at the row's right edge), so
 *  we branch on `mobile`. */
function NavBadgeLink({
  to,
  label,
  unread,
  mobile,
  onClick,
  ariaSuffix,
}: {
  to: string;
  label: string;
  unread: number;
  mobile: boolean;
  onClick?: () => void;
  ariaSuffix: string;
}) {
  if (mobile) {
    return (
      <MobileLink to={to} onClick={onClick ?? (() => {})} badge={unread}>
        {label}
      </MobileLink>
    );
  }
  return (
    <Link to={to} className="hidden md:inline relative text-sm text-slate-600 hover:text-slate-900">
      {label}
      {unread > 0 && (
        <span
          className="absolute -top-2 -right-3 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-semibold flex items-center justify-center"
          aria-label={`${unread} ${ariaSuffix}`}
        >
          {unread > 99 ? "99+" : unread}
        </span>
      )}
    </Link>
  );
}

function MyListingsLink({ mobile, onClick }: { mobile: boolean; onClick?: () => void }) {
  const { counts } = useUnread();
  return (
    <NavBadgeLink
      to="/my-listings"
      label="My listings"
      unread={counts.listings}
      mobile={mobile}
      onClick={onClick}
      ariaSuffix="unread on your listings"
    />
  );
}

function ClassmatesLink({ mobile, onClick }: { mobile: boolean; onClick?: () => void }) {
  const { counts } = useUnread();
  return (
    <NavBadgeLink
      to="/classmates"
      label="Classmates"
      unread={counts.dms}
      mobile={mobile}
      onClick={onClick}
      ariaSuffix="unread DMs"
    />
  );
}

function MyInquiriesLink({ mobile, onClick }: { mobile: boolean; onClick?: () => void }) {
  const { counts } = useUnread();
  return (
    <NavBadgeLink
      to="/my-inquiries"
      label="My inquiries"
      unread={counts.inquiries}
      mobile={mobile}
      onClick={onClick}
      ariaSuffix="unread on your inquiries"
    />
  );
}

function SignInPage() {
  return (
    <div className="flex justify-center pt-8">
      <SignIn routing="path" path="/sign-in" signUpUrl="/sign-in" afterSignInUrl="/my-classes" afterSignUpUrl="/my-classes" />
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
