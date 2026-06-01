import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ClerkProvider } from "@clerk/clerk-react";
import App from "./App";
import { UnreadProvider } from "./hooks/useUnreadCount";
import "./index.css";

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string | undefined;

if (!PUBLISHABLE_KEY) {
  // Fail fast — easier to spot than a cryptic Clerk runtime error.
  // eslint-disable-next-line no-console
  console.error("Missing VITE_CLERK_PUBLISHABLE_KEY in frontend/.env");
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ClerkProvider publishableKey={PUBLISHABLE_KEY ?? ""}>
      <BrowserRouter>
        <UnreadProvider>
          <App />
        </UnreadProvider>
      </BrowserRouter>
    </ClerkProvider>
  </React.StrictMode>,
);
