# School subscriptions

Iga is paid for by schools, not by students. A school administrator pays one flat monthly price (USD 200 by default) and every approved student and teacher of that school gets the full library. Members of schools that haven't paid, and people without a school, still get the free part of the platform.

> Example: Lycée de Kigali paid this month, so all its approved students open every lesson, quiz and past paper. APADE didn't pay, so its students see the free starter lessons and a lock on the rest.

## What is free and what needs a subscription

| Free for every signed-in user | Needs the school's subscription |
|---|---|
| Browsing subjects, units, lesson titles and summaries | The full text of premium lessons (and their translations) |
| Lessons and quizzes marked free (one starter lesson and quiz per subject) | Premium quizzes, and the explanations and marking guides in their results |
| Material written by teachers in the app | Past papers: interactive versions, PDF and marking-guide links |
| Labs and simulations, the code and Python playgrounds | The AI tutor |
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
- When they come back, and whenever Flutterwave's webhook arrives, the server asks Flutterwave's API about the transaction (the one the redirect or webhook names, otherwise by reference). It only extends the subscription if the transaction carries **our reference** and is successful **for the expected currency and at least the expected amount**. Redirect parameters and webhook bodies are never trusted on their own, and webhooks must carry the dashboard's secret hash.
- **A declined attempt is not a failed payment.** The hosted page lets the payer try another card or number with the same reference, so a payment stays pending while its checkout is open and is only marked failed afterwards.
- **A school that paid always gets its months.** A successful transaction confirmed by Flutterwave is applied even if it is reported late, after the payment was marked failed or cancelled. Each payment is applied exactly once, whatever arrives first and however often.
- `reconcile_payments` covers lost webhooks and closed browser tabs: it re-checks open payments from the last `BILLING_RECONCILE_DAYS` (3) days, applies any that succeeded, and marks as cancelled those whose checkout closed without a successful transaction.

**Testing with Flutterwave's test mode:** use test keys, `BILLING_DEV_MODE=false` and a public `FRONTEND_URL` (for example a tunnel). The test cards are listed at developer.flutterwave.com (Testing); expiry dates change, so check them there. To exercise the retry path, pay with the "insufficient funds" test card first and then with a good test card in the same checkout: the subscription must be extended once.

### Bank transfer, cash or free months

Under **Admin → Schools → (school) → Record a payment**, the Iga team records money received outside the app (with the bank reference or receipt number) or free months (amount 0, with the reason). It is applied immediately, audited, and the school administrators get a receipt by email.

### Development and demos

With `BILLING_DEV_MODE=true` (the default when `DJANGO_DEBUG` is on), a test checkout page stands in for Flutterwave. It is refused when the setting is off; never enable it on a real server.

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

- `backend/apps/schools/`: `models.py` (School, Payment, BillingReminder), `access.py` (the one access rule), `membership.py` (joining, approving, removing), `billing.py` (prices, applying payments), `providers.py` and `flutterwave.py` (payment providers), `downloads.py` (signed past-paper downloads), `views.py` and `urls.py` (API), `notify.py` (emails), `management/commands/billing_reminders.py` and `reconcile_payments.py`.
- Gating is applied in the curriculum, assessments, tutor, search and dashboard views; `backend/tests/test_paywall.py` and `test_schools.py` cover it.
- Frontend: `src/components/Locked.jsx`, `src/components/SchoolPicker.jsx`, `src/pages/School.jsx`, the Schools tab in `src/pages/Admin.jsx`.
