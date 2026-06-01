export type User = {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
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

export type Listing = {
  id: string;
  seller: User;
  course: Course | null;
  book_title: string;
  book_author: string;
  book_edition: string | null;
  condition: Condition;
  price_cents: number;
  description: string;
  status: ListingStatus;
  image_url: string | null;
  created_at: string;
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

export type Classmate = {
  id: string;
  display_name: string;
  avatar_url: string | null;
  shared_courses: Course[];
};
