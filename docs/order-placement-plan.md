# Order Placement Plan

**Status:** Proposed; no order-placement code is implemented yet.

## Goal and Scope

Add a separate, controlled execution path for BUY/SELL orders of warrants on Comdirect Livetrading (off-exchange) venues. The first release should support one explicitly selected account/depot, instrument, side, and quantity per intent. It should not make investment decisions or alter the existing read-only sync workflow.

Initial scope includes venue/dimension discovery, Livetrading quote acquisition, the Comdirect TAN challenge handoffs, final order validation and submission, and order-status reconciliation. Order changes and cancellations are follow-up work. Exchange orders and non-QUOTE order types are out of scope unless Livetrading dimensions/API behavior show they are required.

The local API specification is dated April 2020. Before implementing writes, confirm the paths, payloads, TAN behavior, quote lifetime, instrument eligibility, and account permissions against current Comdirect documentation and a suitable account/test arrangement. In particular, the quote-request prose calls the venue field `venue`, while order schemas/examples use `venueId`; verify the actual accepted request field before fixing model aliases.

## Current Baseline

- `ComdirectClient` owns authentication, session state, token refresh, and HTTP calls.
- It currently implements only `get_depot_orders()` and `get_order()` for the Orders API.
- `models/orders.py` contains a response-oriented `Order` model, including `quote_id` and `quote_ticket_id`; typed dimensions, quote, request, cost, and TAN-challenge models are not present.
- The current `functions/sync/` workflow is a read/snapshot pipeline and must never submit orders.

## Proposed Structure

- Extend `ComdirectClient` with authenticated, low-level methods for order dimensions, quote tickets, quote requests, order validation, cost indication, and submission. Reuse its authentication; do not create a second client or duplicate token/TAN logic.
- Add typed request and response models in `src/comdirect_api/models/orders.py`. Keep order-command payloads distinct from response models where their fields or validation rules differ. Use `Decimal` for prices and quantities and preserve Comdirect camelCase aliases.
- Add orchestration and persistence under a separate `functions/orders/` package, for example `order_service.py`, `order_repo.py`, and `run.py`. Keep this separate from `SyncService` and its MongoDB snapshot collections.
- Add a dedicated execution entry point and, only after the local flow is proven, a separate `.github/workflows/place-order.yml`. Never add write operations to `.github/workflows/sync.yml`.
- Persist an auditable order intent and its state transitions in a dedicated `order_intents` collection or equivalent durable store. Never store PINs, OAuth tokens, or TAN challenge values there.

## Livetrading Request Flow

1. **Create intent.** Validate the requested account/depot, warrant identifier, BUY/SELL side, positive quantity, and configured size/notional limits. Assign a unique `intent_id`; do not accept arbitrary raw API payloads from callers.
2. **Discover dimensions.** Call `GET /brokerage/v3/orders/dimensions` for the instrument, side, `orderType=QUOTE`, and `type=OFF`. Select only a returned Livetrading venue and supported parameters. Surface target-market, key-information, and other compliance notices to the operator; do not silently discard them.
3. **Authorize before requesting a quote.** Obtain deliberate approval for the exact intent before quote acquisition, or require an immediate in-process confirmation after showing the quote. Quotes have a short validity window, so do not insert an unpredictable GitHub Environment/reviewer wait between quote retrieval and submission.
4. **Initialize the quote ticket.** Call `POST /brokerage/v3/quoteticket` with the minimum documented order fields (`depotId`, `instrumentId`, `side`, `venueId`, `quantity`). Capture the returned `quoteTicketId` and TAN challenge from the response without logging the challenge.
5. **Authorize the quote request.** Call `PATCH /brokerage/v3/orders/quoteticket/{quoteTicketId}` with the TAN challenge as required by the API. Then call `POST /brokerage/v3/quotes` to request the Livetrading quote.
6. **Check and present the quote.** Validate that the returned quote matches the requested instrument, venue, side, and quantity; record its `quoteId`, price, and expiry. Reject an expired, incomplete, mismatched, or out-of-policy quote. Show the effective price, estimated total, available quote quantity, costs where available, and expiry before confirmation.
7. **Final validation and submission.** Build one immutable `QUOTE` order payload referencing the same `quoteTicketId` and `quoteId`, with matching instrument, venue, side, and quantity. Request any supported ex-ante cost indication with `POST /brokerage/v3/orders/costindicationexante`. Then call `POST /brokerage/v3/orders/validation`, capture its fresh TAN challenge, and immediately call `POST /brokerage/v3/orders` with the identical validated payload and required challenge header.
8. **Reconcile.** Persist the returned Comdirect order ID and response, then use the existing order-read methods to check status and executions. Represent accepted/open, partially executed, executed, rejected, expired, and unknown outcomes explicitly.

The preliminary `POST /brokerage/v3/orders/prevalidation` endpoint may be useful for validating an order draft, but it does not replace the required final validation immediately before submission. Confirm its role in the actual Livetrading flow before making it mandatory.

## Safety and Reliability

- Start in preview/dry-run mode: dimensions and quote discovery are allowed, submission is disabled. Require an explicit live-mode switch for any write call.
- Bind approval to an immutable intent (account, depot, instrument, side, quantity, venue, quote parameters, and configured limits). Any change invalidates approval and requires a new quote/approval.
- Enforce account/depot and venue allowlists, warrant-only instrument checks, maximum quantity/notional, and an operator-defined price/spread tolerance. Fail closed when dimensions, compliance notices, or quote data are missing or ambiguous.
- Quote validity is time-sensitive. Set a short internal deadline from the returned validity; abort rather than submit if the quote is expired or the process is delayed.
- Never blindly retry quote-ticket authorization, order validation, or order submission. On timeout after a write, mark the intent `unknown`, query Comdirect for a matching order, and require reconciliation before any resubmission. Use a unique local `intent_id` to prevent duplicate local executions; do not assume the Comdirect endpoint provides idempotency.
- Record state transitions and sanitized API outcomes for audit. Redact credentials, access tokens, TAN challenges, and sensitive response headers from logs and persisted diagnostics.
- Do not allow automatic execution to make discretionary trading choices. If unattended operation is later desired, require an explicit bounded policy and apply all size, price, venue, and exposure limits before the quote is requested.

## Implementation Phases

### Phase 0: Confirm Requirements and API Behavior

- Confirm which Comdirect logins/depots may trade warrants and whether the account can use Livetrading.
- Verify the live API paths, request/response schemas, TAN header forwarding, quote validity semantics, and cost-indication support.
- Choose the initial confirmation channel and define maximum quantity/notional and price tolerance.
- Document which compliance notices must block or require acknowledgement.

**Exit gate:** written acceptance criteria and an agreed manual-approval policy; no writes enabled.

### Phase 1: Models and Read-Only Discovery

- Add typed order dimensions, quote, cost indication, quote-ticket, and request models.
- Implement `get_order_dimensions()` and test filters, parsing, optional notices, and token refresh.
- Add instrument/venue/side/type validation for warrant Livetrading without placing orders.

**Exit gate:** fixtures from sanitized real or official responses parse correctly; no live order endpoint is called.

### Phase 2: Quote-Only Preview

- Implement quote-ticket creation, TAN challenge forwarding, and quote request methods.
- Add an order-intent state machine and durable audit records.
- Build a preview command that returns the quote, costs, and expiry but cannot submit.
- Test expiry, mismatches, unsupported venues, TAN errors, 422 responses, and sanitized logging.

**Exit gate:** repeated preview runs are safe and never create an order.

### Phase 3: Guarded Single-Order Submission

- Implement final quote-order validation and submission with the exact validation payload and challenge handoff.
- Require approval tied to the immutable order intent and enforce live-mode limits.
- Reconcile status after submission; handle ambiguous timeouts as `unknown` and block retries pending reconciliation.
- Keep the first real-money test deliberately small and operator-supervised, after all mocked tests pass.

**Exit gate:** a reviewed end-to-end test demonstrates one accepted order, correct status reconciliation, and no duplicate on simulated timeout.

### Phase 4: Operational Hardening

- Add structured audit/reporting, alerting for unknown/rejected orders, and credential rotation/runbook guidance.
- Add a separate GitHub Actions workflow only if the approval design is compatible with the quote's short lifetime. Any reviewer gate must occur before quote acquisition; do not pause between quote and submit.
- Consider bounded unattended execution only after review of authorization, monitoring, loss/exposure limits, and emergency-stop behavior.

## Test Plan

- Unit-test each request method for URL, query parameters, JSON aliases, authentication headers, TAN challenge forwarding, token refresh, and HTTP errors.
- Test the quote-to-order state machine with mocked time, expired/mismatched quotes, retries, and duplicate intents.
- Test repository persistence and unique `intent_id` behavior, including restart/reconciliation after an uncertain submission.
- Keep all automated tests mocked; never submit a real order in CI.
- Run the full suite and Ruff before enabling a live execution path. Real-account tests require explicit operator action and must not be part of routine CI.

## Decisions Before Implementation

- Which account and depot are permitted for the initial test?
- Should live submission initially require immediate local confirmation, or a separately approved bounded workflow?
- What are the maximum quantity/notional and acceptable quote-price deviation?
- Which venues should be allowed, and should the client restrict instrument IDs/WKNs to an explicit allowlist?
- Where should the durable order-intent/audit store live, and which consumer application (if any) will initiate an intent?
