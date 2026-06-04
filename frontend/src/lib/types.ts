export type User = {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
  // True once this user has finished Stripe Connect onboarding (their
  // account can charge). Drives whether "Pay with Stripe" appears on
  // listings they're selling.
  stripe_onboarded: boolean;
};

export type Course = {
  id: string;
  code: string;
  title: string;
};

export type EnrollmentKind = "past" | "current" | "upcoming";

export type Enrollment = {
  id: string;
  course: Course;
  term: string;
  kind: EnrollmentKind;
};

export type Condition = "new" | "like_new" | "good" | "fair" | "poor";
export type ListingStatus = "active" | "reserved" | "sold" | "withdrawn";
export type ListingCategory =
  | "book"
  | "furniture"
  | "electronics"
  | "clothing"
  | "kitchen"
  | "decor"
  | "sports"
  | "transportation"
  | "other";

/** Pretty labels for the Everything Else category enum. */
export const NON_BOOK_CATEGORIES: { value: Exclude<ListingCategory, "book">; label: string }[] = [
  { value: "furniture", label: "Furniture" },
  { value: "electronics", label: "Electronics" },
  { value: "clothing", label: "Clothing" },
  { value: "kitchen", label: "Kitchen" },
  { value: "decor", label: "Decor" },
  { value: "sports", label: "Sports" },
  { value: "transportation", label: "Transportation" },
  { value: "other", label: "Other" },
];

/** Payment methods the seller is willing to accept on a listing. The
 *  enum is enforced by the backend's Pydantic Literal — keep this in
 *  sync with `PaymentMethod` in `backend/app/schemas/common.py`.
 *
 *  `in_app: true` means the platform actually processes the payment
 *  (we have a Stripe Connect integration that handles the checkout
 *  end-to-end). `in_app: false` means the buyer and seller arrange the
 *  transfer themselves outside the app — we just signal that the seller
 *  is willing to accept that method.
 */
export type PaymentMethod = "cash" | "venmo" | "zelle" | "paypal" | "stripe";

export const PAYMENT_METHODS: {
  value: PaymentMethod;
  label: string;
  in_app: boolean;
}[] = [
  { value: "cash", label: "Cash", in_app: false },
  { value: "venmo", label: "Venmo", in_app: false },
  { value: "zelle", label: "Zelle", in_app: false },
  { value: "paypal", label: "PayPal", in_app: false },
  { value: "stripe", label: "Stripe", in_app: true },
];

export type Listing = {
  id: string;
  seller: User;
  course: Course | null;
  category: ListingCategory;
  title: string;
  // Nullable for non-book listings.
  author: string | null;
  edition: string | null;
  condition: Condition;
  price_cents: number;
  description: string;
  status: ListingStatus;
  image_url: string | null;
  payment_methods: PaymentMethod[];
  created_at: string;
  // Only populated by GET /api/me/listings. 0 elsewhere.
  unread_count: number;
};

export type MatchedListing = Listing & {
  rationale: string;
  score: number;
};

export type Message = {
  id: string;
  conversation_id: string;
  sender_id: string;
  body: string;
  created_at: string;
  read_at: string | null;
};

export type Conversation = {
  id: string;
  // Null for direct-message conversations (started from the Classmates page).
  listing: Listing | null;
  buyer: User;
  other_user: User;
  updated_at: string;
  last_message: Message | null;
  // Incoming messages addressed to the viewer that aren't yet read.
  unread_count: number;
};

/** A course shared with a classmate, annotated with the OTHER user's
 *  enrollment kind for that course. The viewer's own kind is always
 *  "current" — those are the courses the classmates query is scoped to. */
export type SharedCourse = Course & { kind: EnrollmentKind };

/** Public-facing user profile returned by GET /api/users/:id.
 *  Deliberately narrower than User — no email, no stripe_onboarded. */
export type PublicUser = {
  id: string;
  display_name: string;
  avatar_url: string | null;
  active_listings: Listing[];
};

export type Classmate = {
  id: string;
  display_name: string;
  avatar_url: string | null;
  shared_courses: SharedCourse[];
  // Null = no DM has been started with this classmate yet (clicking on
  // the row will create one). Set = the existing DM's id.
  dm_conversation_id: string | null;
  // Incoming messages from this classmate in our DM the viewer hasn't
  // read yet. Drives the per-row red badge.
  unread_count: number;
};
