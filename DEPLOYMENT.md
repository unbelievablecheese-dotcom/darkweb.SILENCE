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
Coach-only tools stay locked until the owner approves the request. Configure
these private Render environment variables before enabling coach signup:

- `PUBLIC_BASE_URL`: the public HTTPS URL of the deployed site, without a
  trailing slash (for example, `https://your-site.onrender.com`).
- `SMTP_HOST`: your outgoing email provider's SMTP host. For Gmail, use
  `smtp.gmail.com`.
- `SMTP_PORT`: `587` for STARTTLS or `465` for SMTP SSL.
- `SMTP_USERNAME`: the sending email account.
- `SMTP_PASSWORD`: the provider's app password or SMTP credential, never the
  account's ordinary sign-in password.
- `SMTP_FROM`: the sender address; it can be the same as `SMTP_USERNAME`.

For Gmail, enable 2-Step Verification on the sending account and create a
Google App Password. Do not use or share the Gmail account's regular password.
Keep `SECRET_KEY` stable across restarts and redeploys so pending approval links
remain valid. After adding these settings, redeploy. Coach applications will
then be available from the **COACH?** button on the sign-in page. The approval
email goes to `unbelievablecheese@gmail.com`; opening its seven-day link shows
the applicant details and requires clicking **APPROVE COACH**. The email link
is single-use, and link previews do not approve requests.

## Match center, tryout tracking, profiles, and news

- Approved coaches can open **SITE UPDATES** to publish announcements, add
  confirmed upcoming fixtures with optional stream links, and edit public
  roster profiles. Only publish player-approved profile details; blank fields
  stay hidden. The team's existing VLR result snapshot is still maintained in
  the app code and should be checked against VLR before being updated.
- The **MATCHES** page shows that snapshot and coach-published upcoming games.
  Tournament standings and live results remain linked to VLR rather than being
  guessed or presented as an automatic live feed.
- Applicants receive a one-time private tracking code after submitting the
  questionnaire. They must save it to check review status later; it is stored
  as a hash and cannot be recovered if lost. Coaches update the status from
  **COACH REVIEW**.
- The optional **SILENCE RADIO** button opens the YouTube video in a reusable
  separate window, set to loop, so it can continue while visitors navigate
  the site. Playback starts only after a visitor chooses the button; browser
  settings or the video's embedding availability may require pressing Play in
  the YouTube controls.
