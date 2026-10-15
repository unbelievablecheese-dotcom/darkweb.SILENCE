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
