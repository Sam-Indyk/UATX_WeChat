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

export type Enrollment = {
  id: string;
  course: Course;
  term: string;
  is_current: boolean;
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
  listing: Listing;
  buyer: User;
  updated_at: string;
  last_message: Message | null;
};

export type Classmate = {
  id: string;
  display_name: string;
  avatar_url: string | null;
  shared_courses: Course[];
};
