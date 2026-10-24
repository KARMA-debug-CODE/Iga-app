# School subscriptions

Iga is paid for by schools, not by students. A school administrator pays one flat monthly price (USD 200 by default) and every approved student and teacher of that school gets the full library. Members of schools that haven't paid, and people without a school, still get the free part of the platform.

> Example: Lycée de Kigali paid this month, so all its approved students open every lesson, quiz and past paper. APADE didn't pay, so its students see the free starter lessons and a lock on the rest.

## What is free and what needs a subscription

| Free for every signed-in user | Needs the school's subscription |
|---|---|
| Browsing subjects, units, lesson titles and summaries | The full text of premium lessons (and their translations) |
| Lessons and quizzes marked free (one starter lesson and quiz per subject) | Premium quizzes, and the explanations and marking guides in their results |
| Material written by teachers in the app | Past papers: interactive versions, PDF and marking-guide links |
| Labs and simulations, the code and Python playgrounds | Santa, the AI tutor |
| A class's hardest units, and how many misconceptions a teaching pack would find | Teaching packs: what the class gets wrong, a CBC lesson plan, a three-level worksheet and a targeted quiz from the class's own results |
| Classes, assignments of free material, marking, study groups, leaderboards, parent reports | Saving premium units for offline use |

Content files decide what is free: `access: free` in a lesson's front matter, `"access": "free"` in a quiz file. Everything else from the library is premium. A teacher's own lessons and quizzes are free, but a quiz that reuses library questions is premium, so library material can't be repackaged.

## How a school joins

1. **The school administrator registers** on the sign-up page as *School staff* and chooses **Register my school** (name, district, phone). The school waits for verification.
2. **The Iga team verifies** the school under **Admin → Schools**. Verifying also approves the person who registered it as the school's first administrator. More administrators can register by choosing the school; an existing administrator or the Iga team approves them. A registration that isn't a real school can be **rejected** (deleted) while it is still waiting, so it doesn't keep the name taken.
3. **Students and teachers choose their school** when they sign up (or later, under *Profile → My school*):
   - with the **school code** (shown on the administrator's home page), they are approved straight away;
   - without it, they wait until a school administrator approves them under **Members**. Approving a teacher also confirms them as a teacher (they can create classes); teachers who joined with the code are confirmed with **Confirm as teacher**. A school's confirmation lasts while the teacher is a member: if they leave or are removed, it ends. Teachers approved by the Iga team keep their approval, and a school can't restore an approval the Iga team withdrew.
   - Students created by a teacher from a class list join the teacher's school automatically.
4. **The administrator pays** under **Subscription**: 1, 3, 6 or 12 months. Renewing early adds to the current end date, so no days are lost.

A school administrator can remove members and issue a new school code at any time (members already in stay; the old code stops working).

## Subscription states

| State | Meaning | Students get |
|---|---|---|
| Not subscribed | The school has never paid | Free part only |
| Active | Paid until a future date | Everything |
| Grace | Ended less than `SUBSCRIPTION_GRACE_DAYS` (3) ago | Everything, while the school renews |
| Ended | Ended longer ago | Free part only |

A suspended school (Admin → Schools → Suspend) loses access whatever it paid, and its administrators lose their administrator pages until the Iga team reinstates it.

If access ends while a student is in the middle of a premium quiz, the attempt is closed with what they answered, and their result stays visible (without the premium explanations).

## Paying

### Online (Flutterwave: cards, MTN MoMo and Airtel Money)

1. Create a Flutterwave business account on the **v3 API** (secret keys look like `FLWSECK-...`; test keys `FLWSECK_TEST-...`). Flutterwave accounts use one API version; if the dashboard only offers v4 client credentials, the provider needs porting first.
2. In the dashboard under **Settings → Webhooks**, in both test and live mode:
   - set the URL to `https://<your-domain>/api/billing/webhooks/flutterwave/` and choose a long random **secret hash**;
   - tick **Receive webhook response in JSON format**, **Enable v3 webhooks**, **Enable webhook retries** and **Enable resend webhook from the dashboard**. (Iga also understands Flutterwave's form-encoded and legacy bodies, and logs a warning when a webhook carries no reference, but JSON v3 is the tested setup.)
3. Set `BILLING_PROVIDER=flutterwave`, `FLUTTERWAVE_SECRET_KEY`, `FLUTTERWAVE_WEBHOOK_HASH` (the same secret hash) and `FRONTEND_URL` (the public HTTPS address people come back to after paying).
4. **Set `SUBSCRIPTION_PRICE_RWF`** (whole francs, e.g. the USD price at your chosen rate). Rwandan mobile money (MTN MoMo, Airtel Money) only works in francs, so with a USD price alone schools can only pay by card. Card payments in USD keep working alongside.
5. Make sure the `scheduler` service (or a cron job) runs `python manage.py reconcile_payments` every few minutes; see below.

What happens:

- Iga creates a pending payment with its own reference (`tx_ref`) and sends the administrator to Flutterwave's hosted page, which stays open for `CHECKOUT_SESSION_MINUTES` (60) and allows `FLUTTERWAVE_MAX_RETRIES` (5) attempts.
- When they come back, and whenever Flutterwave's webhook arrives, the server asks Flutterwave's API about the transaction (the one the redirect or webhook names, otherwise by reference). It only extends the subscription if the transaction carries **our reference** and is successful **for the expected currency and at least the expected amount**. Redirect parameters and webhook bodies are never trusted on their own: they only say which transaction to look up.
- **Webhooks must be signed.** A webhook must carry the dashboard's secret hash in `verif-hash` (v3), or in `flutterwave-signature` a base64 HMAC-SHA256 of the exact body under that secret; both are compared in constant time, and without `FLUTTERWAVE_WEBHOOK_HASH` every webhook is refused. Each refused delivery (bad or missing signature, unreadable body) is logged and written to the audit log (at most 30 a minute per address, so forgeries can't fill it). A delivery with the same body as one already handled is a replay: it is acknowledged and audited but not acted on, and Flutterwave's API isn't asked again, unless the first delivery couldn't reach a final answer (Flutterwave unreachable, or the transaction still pending), in which case it is checked again after a minute. Every delivery is kept as a `WebhookEvent` (Django admin, read-only).
- One Flutterwave transaction can pay for one payment only (a unique constraint, checked again before applying), and a successful transaction that doesn't match (another currency, a smaller amount, another school) is refused and audited as `payment_rejected`.
- **A declined attempt is not a failed payment.** The hosted page lets the payer try another card or number with the same reference, so a payment stays pending while its checkout is open and is only marked failed afterwards.
- **A school that paid always gets its months.** A successful transaction confirmed by Flutterwave is applied even if it is reported late, after the payment was marked failed or cancelled. Each payment is applied exactly once, whatever arrives first and however often.
- `reconcile_payments` covers lost webhooks and closed browser tabs: it re-checks open payments from the last `BILLING_RECONCILE_DAYS` (3) days, applies any that succeeded, and marks as cancelled those whose checkout closed without a successful transaction.

**Testing with Flutterwave's test mode:** use test keys, `BILLING_DEV_MODE=false` and a public `FRONTEND_URL` (for example a tunnel). The test cards are listed at developer.flutterwave.com (Testing); expiry dates change, so check them there. To exercise the retry path, pay with the "insufficient funds" test card first and then with a good test card in the same checkout: the subscription must be extended once.

### Bank transfer, cash or free months

Under **Admin → Schools → (school) → Record a payment**, the Iga team records money received outside the app (with the bank reference or receipt number) or free months (amount 0, with the reason). It is applied immediately, audited, and the school administrators get a receipt by email. A bank or receipt reference can be recorded only once (compared without case or extra spaces, across all schools), and the page sends an `Idempotency-Key` with each payment it records, so a double click or a resend after a network error records it once.

### Prices come from the server

The amount, currency, plan and number of months of a checkout come only from `SUBSCRIPTION_PRICES` and `SUBSCRIPTION_MONTH_OPTIONS`: the browser chooses one of the offered month counts and currencies, and anything else it sends (an amount, a price, a plan, a number of days) is ignored. A price that is missing, zero, negative or not a number refuses checkout (503) instead of creating a free one. The amount owed is fixed when the checkout starts, so a later price change doesn't alter it, and Flutterwave's verified answer must show at least that amount, in that currency, for that reference (and that school, when it echoes our `meta`). Platform administrators set the amount of a payment they record by hand, because it is what the bank actually received.

## Money: what is computed and recorded

For every applied payment the server stores, on the payment and in the ledger:

| Field | Card / mobile money (Flutterwave) | Recorded by the Iga team |
|---|---|---|
| **gross** | `charged_amount` from Flutterwave's verify API (what the payer was charged; it includes Flutterwave's fee when the customer bears it), or `amount` when `charged_amount` is missing or lower | the amount entered |
| **provider fee** | `app_fee` from the same verified answer; 0 when Flutterwave gives none, a negative one, or one larger than gross | 0 |
| **net** | gross - provider fee: what reaches Iga's account | the amount entered |

Nothing in a webhook body or a redirect is used for these numbers: they come from the provider's API answer that also confirmed the payment. Amounts are rounded to cents. Iga has no partners, resellers or platform commission, so nothing else is deducted; the provider's fee is the only one. The prices schools pay (`amount`) are kept next to gross, so the two can differ when the payer bears the fee.

Platform administrators see gross, fee and net for each payment (Admin → Schools → a school), the totals per currency in Admin → Statistics ("provider fees in total", "received in total, after fees and refunds"), and every entry in the CSV export (**Export the ledger**, or `GET /api/admin/ledger/export/?school=&since=&until=`). School administrators see only the price they paid.

### The money ledger

Every money event is one entry in `LedgerEntry` (`apps/schools/ledger.py`), written in the same database transaction as the change it records: an applied payment, free months, a refund, a correction. Each entry holds the kind, school, payment, currency, gross, provider fee, net, months added or taken back, the paid-through date before and after, the bank or provider reference, who recorded it and why.

- **Append-only.** The model refuses to save a changed entry or delete one, the Django admin shows them read-only, and on PostgreSQL a trigger (migration `schools.0005`) refuses `UPDATE` and `DELETE` on the table whoever runs them; the app's database role cannot `TRUNCATE` or drop it either. Schools with ledger entries can't be deleted. The paid-through date can only move through a payment or a ledger entry (it is read-only in the Django admin and in every API).
- **Corrections are new entries.** A refund (a negative amount, optionally taking months back) or a correction (an amount and/or months, pointing at the entry it corrects with its number) is recorded under Admin → Schools → a school → **Record a refund or correction**, or `POST /api/admin/schools/<id>/ledger/`. It needs a password confirmed in the last few minutes, an `Idempotency-Key` makes a resend harmless, and it is audited.
- **Hash-chained.** Each entry stores the hash of the previous one and its own hash over all its fields (SHA-256, or HMAC-SHA256 with `LEDGER_HMAC_KEY`, so someone who can write to the database but doesn't know the key can't rebuild the chain). `python manage.py verify_ledger` recomputes the chain and checks that every paid payment has exactly one entry with the same amount; it reports an edited, removed, inserted or reordered entry and exits with an error. Keep the head it prints (`SEQ:HASH`) somewhere else (a ticket, an email) and pass it back with `--expect-head SEQ:HASH` next time: that also catches a ledger rebuilt from scratch or cut short.
- Payments applied before the ledger existed got their entries, oldest first, when the migration ran.

### Development and demos

With `BILLING_DEV_MODE=true` (the default when `DJANGO_DEBUG` is on), a test checkout page stands in for Flutterwave. It is refused when the setting is off, and a payment started with it is never confirmed once the setting is off. A real deployment (`DJANGO_DEBUG` off, `HTTPS` on) refuses to start with it on (check `iga.E010`) or with a Flutterwave test key (`iga.E011`); only a staging server that takes test payments on purpose sets `BILLING_ALLOW_TEST_PAYMENTS=true`.

## Upgrading an existing installation

`python manage.py migrate` (run by the Docker image on start) does everything access needs: it adds the school tables, opens the free starter lesson and quiz of each subject, makes teachers' own material free (but not teacher quizzes that reuse library questions), and moves Kinyarwanda and Kiswahili interface settings to English. Then run `python manage.py load_curriculum` once to load the French lesson translations, unit and subject names; it is safe to run again. Nobody has premium access until their school is verified, they are approved members, and the school has paid (or the Iga team records a payment).

## Receipts and reminders

- School administrators see every payment under **Subscription**, with printable receipts. These are not official tax invoices: if the business must issue EBM invoices (Rwanda Revenue Authority), issue them separately.
- `python manage.py billing_reminders` emails school administrators 7, 3 and 1 day(s) before the subscription ends and when it has ended. It is safe to run repeatedly (each reminder is sent once per end date).
- `python manage.py reconcile_payments` re-checks open online payments (see *Paying*). It is also safe to run repeatedly.
- The Docker setup runs both every 10 minutes in the `scheduler` service; elsewhere, use cron.
- Configure email with `EMAIL_BACKEND` and the `EMAIL_*` settings (the default prints emails to the console).

## Demo accounts (`seed_demo`, password `Iga-demo-2026`)

| Username | Role | School |
|---|---|---|
| `lkadmin` | School administrator | Lycée de Kigali (subscribed for a month) |
| `aline`, `eric`, `divine`, `kevin`, `teacher` | Students, teacher | Lycée de Kigali |
| `apadeadmin` | School administrator | APADE (not subscribed) |
| `samuel`, `grace` | Students | APADE |
| `gsadmin` | School administrator | GS Remera Catholique (waiting for verification) |
| `admin` | Iga team | — |

## Where it lives in the code

- `backend/apps/schools/`: `models.py` (School, Payment, LedgerEntry, WebhookEvent, BillingReminder), `access.py` (the one access rule), `membership.py` (joining, approving, removing), `billing.py` (prices, applying payments, refunds and corrections), `ledger.py` (the money ledger and its verification), `webhooks.py` (refused and replayed webhook deliveries), `checks.py` (settings a real deployment refuses), `providers.py` and `flutterwave.py` (payment providers), `downloads.py` (signed past-paper downloads), `views.py` and `urls.py` (API), `notify.py` (emails), `management/commands/billing_reminders.py`, `reconcile_payments.py` and `verify_ledger.py`.
- Attacks on payments are tested in `backend/tests/test_billing_security.py` (webhooks, redirects, prices, settings), `test_ledger.py` (the ledger) and `test_money_concurrency.py` (racing requests, on PostgreSQL).
- Gating is applied in the curriculum, assessments, tutor, search and dashboard views; `backend/tests/test_paywall.py` and `test_schools.py` cover it.
- Frontend: `src/components/Locked.jsx`, `src/components/SchoolPicker.jsx`, `src/pages/School.jsx`, the Schools tab in `src/pages/Admin.jsx`.
