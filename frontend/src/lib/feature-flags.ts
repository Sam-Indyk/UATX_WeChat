/** Feature flags for staged rollouts. Flip these together with any
 *  coordinated backend / Clerk / Railway changes.
 */

/** When false, the Stripe Connect UI is grayed out across the app:
 *  - "Stripe" checkbox on the New Listing + New Item forms is disabled.
 *  - "Connect with Stripe" button in Settings is disabled.
 *  - "Pay with Stripe" button on listing details still works for
 *    any LEGACY listing whose seller was onboarded before the gate
 *    flipped — we don't break in-flight transactions, we just stop
 *    accepting NEW sign-ups for Stripe.
 *
 *  All the Stripe code (backend router, webhook handlers, schema)
 *  stays. Flip this to true once we've validated production payment
 *  flow with real students. */
export const STRIPE_ENABLED = false;
