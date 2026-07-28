# Putting the tool online (plain-English guide)

This is the click-by-click way to take the tool from "runs on my laptop" to "a
link my users can open in a browser." No coding. Budget about 30 minutes the
first time.

**What you'll end up with:** a web address like `ef-explainer.streamlit.app`
that anyone can open. Everyone can use the tool for free on the built-in offline
explanations. The AI-written explanations (which cost API money) are unlocked by
signing in with Google, and only for people on your approved list.

You do this once. After that, adding or removing a user is a 30-second edit.

---

## The three things this setup gives you

1. **Open front door.** Anyone with the link can run the tool and read the free
   offline explanations. Nobody is turned away, so you never lose a curious
   visitor.
2. **AI behind sign-in.** The paid, client-ready explanations appear only after a
   user signs in with Google and is on your approved list. That is how you keep
   control of who spends your API key.
3. **A spending cap underneath.** A hard monthly limit on your API account, so
   the bill can never surprise you. Set this even if you do nothing else.

---

## Step 1: Set the spending cap (5 minutes, do this first)

This is your seatbelt. It works no matter what else you configure.

1. Go to the **Anthropic Console** at `console.anthropic.com` (or the Google AI
   Studio billing page if you use Gemini).
2. Open **Billing → Usage limits** (wording may vary slightly).
3. Set a **monthly spend limit** you're comfortable with, for example `$20`.
4. Save.

That's it. If usage ever hits the cap, the AI explanations pause until the next
month or until you raise the limit. Your bill cannot go past the number you set.

---

## Step 2: Get an API key (5 minutes)

The key is a secret password that lets the tool write explanations. You paste it
into the host once, and users never see it.

1. In the **Anthropic Console**, open **API keys → Create key**.
2. Copy the key (starts with `sk-ant-`). Keep it somewhere private for a minute.

**Never** paste this key into the code or into GitHub. It only ever goes into the
host's "Secrets" box (Step 4). If a key is ever exposed, delete it in the Console
and make a new one.

---

## Step 3: Deploy the app to Streamlit Community Cloud (10 minutes)

1. Go to `share.streamlit.io` and sign in with the GitHub account that owns this
   repository.
2. Click **Create app → Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `thelivinsine/susty-automation`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. Click **Deploy**. Wait a couple of minutes while it installs and starts.

You now have a live link. At this point it runs open, on the free offline
explanations, for anyone. The next steps switch on the paid AI for approved users.

---

## Step 4: Add your secrets (the API key)

1. On your app's page in Streamlit Cloud, open **Settings → Secrets**.
2. Paste this one line, with your real key:

   ```
   ANTHROPIC_API_KEY = "sk-ant-your-real-key"
   ```

3. Save. The app restarts automatically.

If you don't add a key at all, the tool still works for everyone on the free
offline explanations. it just won't offer AI-written ones.

---

## Step 5: Turn on Google sign-in (so AI is gated)

This is the one fiddly part. Follow it slowly and it's just copy-paste.

### 5a. Create a Google sign-in credential

1. Go to the **Google Cloud Console** at `console.cloud.google.com`.
2. Create a project (any name), then open **APIs & Services → Credentials**.
3. Click **Create credentials → OAuth client ID**. If asked, configure the
   "consent screen" first: pick **External**, give it an app name and your email,
   and save. You do not need Google's verification for a small user group.
4. For **Application type**, choose **Web application**.
5. Under **Authorized redirect URIs**, add your app's address followed by
   `/oauth2callback`, for example:
   `https://ef-explainer.streamlit.app/oauth2callback`
6. Click **Create**. Copy the **Client ID** and **Client secret**.

### 5b. Add the login + approved-list secrets

Back in Streamlit Cloud, **Settings → Secrets**, add this below your API key
(replace the placeholder values):

```
[auth]
redirect_uri = "https://ef-explainer.streamlit.app/oauth2callback"
cookie_secret = "any-long-random-string-you-make-up"
client_id = "your-client-id.apps.googleusercontent.com"
client_secret = "your-client-secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[access]
emails = ["you@gmail.com"]
domains = []
```

Save. The app restarts, and now shows a **Sign in with Google** button. Only the
emails you list under `[access]` get the AI explanations; everyone else still gets
the free offline ones.

> A safe template of all these settings lives in the repo at
> `.streamlit/secrets.toml.example`. Copy from there if you lose your place.

---

## Day-to-day: adding or removing a user

Open **Settings → Secrets** and edit the `emails` line:

```
[access]
emails = ["you@gmail.com", "colleague@acme.com", "client@bigco.com"]
```

- **Add someone:** add their email, save. They can sign in and get AI right away.
- **Remove someone:** delete their email, save. They drop back to the free
  offline version.
- **Approve a whole company:** put their domain in `domains`, e.g.
  `domains = ["acme.com"]`, so anyone with an `@acme.com` Google account is in.

If you leave both `emails` and `domains` empty, **any** signed-in user gets the
AI, and the app shows you a warning to that effect. Fill in at least your own
email before sharing the link widely.

---

## Frequently asked, plainly answered

**Can a user see my API key?** No. It lives on the server and is used behind the
scenes. It never travels to anyone's browser. The only way a key leaks is if it's
written into the code or committed to GitHub, which this setup never does.

**What if someone not approved opens the link?** They can still use the whole
tool with the free offline explanations. they just see a "Sign in to unlock AI
explanations" note where the AI ones would be. Nothing costs you money.

**What stops strangers running up my bill?** Two things: the approved list (only
your people get the paid AI) and the spending cap (a hard ceiling regardless).

**Do I have to use Google sign-in?** No. If you skip Step 5, the tool runs fully
open. Pair that with the free offline explainer (don't add an API key, or accept
that the cap protects you) if you want zero-friction sharing.

**Do users need to install anything?** No. They open the link in any browser.
That's the whole point.
