# Persistent free database for Render

The app uses SQLite locally by default. On Render, set `DATABASE_URL` to a
hosted PostgreSQL connection string to keep accounts and notes in a database
that survives web-service restarts and redeploys.

## Neon setup

1. Create a PostgreSQL project on [Neon](https://neon.com/) and choose its
   Free plan. Check Neon's current quotas and terms before relying on it.
2. In the Neon dashboard, copy the connection string for the database. Keep it
   private; it contains database credentials.
3. In Render, open the `flask-notes` web service and choose **Environment**.
   Add an environment variable named `DATABASE_URL` and paste the connection
   string as its value. Do not commit the connection string to GitHub.
4. Save the environment change and redeploy the service. The app creates its
   tables automatically when it starts with the configured database.
5. Confirm the deployment succeeded, then create an account on the hosted site.

The app accepts Neon connection strings beginning with either `postgres://` or
`postgresql://` and configures the Psycopg 3 SQLAlchemy driver automatically.
If the connection URL already specifies a SQLAlchemy driver, verify that the
driver is `postgresql+psycopg`.

This changes where new accounts and notes are stored; it does not copy records
from an existing local SQLite database. Back up or migrate any records you
need before switching databases. Keep `GROQ_API_KEY` and `SECRET_KEY`
configured as private Render environment variables as well.

## H.A.R.V.E.Y. with GroqCloud

1. Create an API key in the [GroqCloud console](https://console.groq.com/keys).
2. In Render, open the web service's **Environment** settings and add
   `GROQ_API_KEY` with the key as its value. Never put the key in source code or
   commit it to GitHub.
3. Save the setting and redeploy the service. H.A.R.V.E.Y. uses
   `openai/gpt-oss-120b` by default. To select a different model available
   to your Groq account, set `GROQ_MODEL` to its exact model ID.

## Coach access and player applications

1. Create an account for each trusted coach or manager on the website.
2. For existing trusted coaches or managers, set `COACH_EMAILS` in Render's
   web-service **Environment** settings to a comma-separated list of account
   email addresses, for example `coach@example.com,manager@example.com`. Save
   and redeploy. Newly approved coach requests also grant coach access.
3. Player submissions are stored in the app's configured database. Coaches can
   filter by role, rank, and status, update review status, and export filtered
   applications to CSV for import into a spreadsheet. The app does not email or
   sync submissions to Google Sheets automatically.
4. Applicants must consent before submission. Treat the dashboard and CSV as
   sensitive personal data; limit staff access and remove records when no
   longer needed. Use a persistent database such as Neon in production so
   submissions survive service restarts.

## Coach account approval email

Coach signup creates a normal member account with a pending coach request.
Coach-only tools stay locked until the owner approves the request. A provider
must be configured before coach signup or approval-email resend is enabled.

### Resend HTTPS API (recommended for Render)

1. Create a Resend account and verify a domain you control in its Domains
   settings. Follow Resend's DNS instructions before sending from that domain.
2. Create a Resend API key with permission to send email.
3. In Render's web-service **Environment** settings, add:
   - `EMAIL_PROVIDER` = `resend`
   - `RESEND_API_KEY` = your private Resend API key
   - `RESEND_FROM` = a sender on the verified domain, such as
     `SILENCE <coach@yourdomain.com>`
   - `PUBLIC_BASE_URL` = the deployed site's HTTPS origin, without a path or
     trailing slash, such as `https://your-site.onrender.com`
4. Save changes and wait for Render to redeploy. Keep `SECRET_KEY` stable so
   existing approval links remain valid.

The app sends the approval message to `unbelievablecheese@gmail.com` through
Resend's HTTPS API. The API key is used only on the server and must never go
in frontend code, source control, or chat. After configuring, sign in to the
pending coach account and use **Resend Approval Email**. Check Render logs if
the send still fails, and check the Resend dashboard for API errors or delivery
events.

### SMTP alternative

Alternatively, set `EMAIL_PROVIDER` to `smtp` (or leave it unset), and provide
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and optionally
`SMTP_FROM`. For Gmail SMTP, use `smtp.gmail.com`, port `587`, and an App
Password created after enabling 2-Step Verification; never use the account's
normal password.

The approval email recipient is fixed to `unbelievablecheese@gmail.com`.
Opening the seven-day signed link only shows the request; the owner must click
**APPROVE COACH**. Approval links are single-use, and link previews do not
approve requests.

## Match center, tryout tracking, profiles, and news

- Approved coaches can open **SITE UPDATES** to publish announcements, add
  confirmed upcoming fixtures with optional stream links, and edit public
  roster profiles. Only publish player-approved profile details; blank fields
  stay hidden. The team's existing VLR result snapshot is still maintained in
  the app code and should be checked against VLR before being updated.
- The **MATCHES** page shows that snapshot and coach-published upcoming games.
  Tournament standings and live results remain linked to VLR rather than being
  guessed or presented as an automatic live feed.
- SILENCE player pages show all-time VLR agent-use snapshots and derive the
  most-used VALORANT agent class by summing the maps played on each class's
  agents. A player's leading individual agent can belong to a different class
  than their most-used class. These inferences are not player-confirmed team
  assignments; recheck each linked VLR profile before relying on the snapshot.
- The merch page includes three original vector print studies with direct SVG
  downloads for a designer. These are still concepts, not production approvals
  or product listings; confirm sizing, color separations, materials, and
  embroidery constraints with the designer and manufacturer.
- Applicants receive a one-time private tracking code after submitting the
  questionnaire. They must save it to check review status later; it is stored
  as a hash and cannot be recovered if lost. Coaches update the status from
  **COACH REVIEW**.
- The optional **SILENCE RADIO** button opens the YouTube embed inline on the
  current page and requests looping playback. YouTube controls and video remain
  visible; use a properly licensed audio file if true audio-only playback is
  required. Playback starts only after a visitor chooses the button, and
  browser settings or the video's embedding availability may still require
  pressing Play in YouTube's controls.

  - H.A.R.V.E.Y.'s optional voice replies use the visitor's built-in browser
    speech voices. The voice menu lets each visitor choose an installed English
    voice, remembers that preference in their browser, and uses a slightly
    slower speaking pace. Voice options and how natural they sound depend on
    the visitor's browser and operating system; install a higher-quality English
    voice in the device settings for more natural playback.
