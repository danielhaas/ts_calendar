# TeamSnap Filtered Calendar Feed

A self-hosted calendar subscription feed that shows only the TeamSnap events you've RSVP'd **Yes** or **Maybe** to. Deploy once for your team and everyone can subscribe to their own personalized feed.

The feed matches TeamSnap's native iCal format — team name in summaries, local timezone, location and arrival time in descriptions.

## How It Works

A serverless Python function on Vercel fetches your team's events from the TeamSnap API, filters them by each member's RSVP status, and serves a standard `.ics` calendar feed. Any calendar app (Google Calendar, Apple Calendar, Outlook) can subscribe to it.

## Setup

### 1. Register a TeamSnap App

1. Go to [auth.teamsnap.com](https://auth.teamsnap.com) and sign in
2. Create a new application
3. Set the callback URL to: `urn:ietf:wg:oauth:2.0:oob`
4. Note your **Client ID** and **Client Secret**

### 2. Get Your API Tokens

```bash
git clone https://github.com/danielhaas/ts_calendar.git
cd ts_calendar
pip install -r requirements.txt
python setup_auth.py
```

The script will:
- Ask for your Client ID and Client Secret
- Open your browser to authorize the app
- Give you an **Access Token** and **Refresh Token**

### 3. Deploy to Vercel

Install the [Vercel CLI](https://vercel.com/docs/cli) and log in:

```bash
npm install -g vercel
vercel login
```

Deploy and set your environment variables:

```bash
vercel --prod

vercel env add TEAMSNAP_CLIENT_ID      # paste your Client ID
vercel env add TEAMSNAP_CLIENT_SECRET   # paste your Client Secret
vercel env add TEAMSNAP_ACCESS_TOKEN    # paste your Access Token
vercel env add TEAMSNAP_REFRESH_TOKEN   # paste your Refresh Token
vercel env add FEED_PASSWORD            # optional: password to protect the members page

vercel --prod   # redeploy with env vars
```

### 4. Find Your Team ID

Your team ID is in the URL when you view your team on TeamSnap:
`https://go.teamsnap.com/team/schedule?team_id=XXXXX`

### 5. Share With Your Team

Send your teammates this link (replace `YOUR_TEAM_ID` and `your-app.vercel.app`):

```
https://your-app.vercel.app/api/members?team_id=YOUR_TEAM_ID
```

If you set a `FEED_PASSWORD`, teammates will be prompted to enter it before they can see the member list. They select their name from the dropdown, copy the calendar URL, and add it as a subscription in their calendar app.

## Endpoints

| Endpoint | Description |
|---|---|
| `/api/members?team_id=XXXXX` | Interactive page for teammates to get their calendar URL (password-protected if `FEED_PASSWORD` is set) |
| `/api/calendar?team_id=XXXXX` | Calendar feed for the token owner |
| `/api/calendar?team_id=XXXXX&member_id=YYYYY` | Calendar feed for a specific team member |

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TEAMSNAP_CLIENT_ID` | Yes | From TeamSnap developer portal |
| `TEAMSNAP_CLIENT_SECRET` | Yes | From TeamSnap developer portal |
| `TEAMSNAP_ACCESS_TOKEN` | Yes | From `setup_auth.py` |
| `TEAMSNAP_REFRESH_TOKEN` | Yes | From `setup_auth.py` |
| `FEED_PASSWORD` | No | Password to protect the members page |

## Local Development

```bash
cp .env.example .env
# fill in your values in .env
pip install -r requirements.txt
python serve_local.py
# visit http://localhost:3000/api/members?team_id=YOUR_TEAM_ID
```

## Limitations

- Access tokens expire after ~2 hours. The app auto-refreshes them, but refreshed tokens only persist in memory on warm serverless instances. If your token stops working, re-run `setup_auth.py`.
- Only events from the last 30 days onward are included.
- Calendar apps may take 12-24 hours to pick up feed changes (Google Calendar limitation).
