# stockwatch

Hourly scanner for European equities. Free data only, no API keys, runs on
GitHub Actions.

## What it watches

- **Price and volume** — Yahoo's chart endpoint, which covers Oslo, Stockholm,
  Copenhagen, Helsinki, XETRA, Paris, Amsterdam and London.
- **Oslo Børs NewsWeb** — official Norwegian disclosures, labelled regulatory or
  not. Companies must publish material information here first.
- **MFN** — Nordic disclosures beyond Oslo.

Regulated disclosure feeds are the reason European coverage is better than a US
equivalent would be: this reads the filing itself, not a news site's account
of it.

## What counts as a signal

Two rules, both there to stop it becoming a noise generator.

**Everything is relative.** Moves are scored in standard deviations of that
instrument's own recent returns, not percent. Volume is scored against a rolling
*median*, so last week's spike does not quietly raise the bar for noticing the
next one.

**The market is subtracted.** The baseline is the watchlist's own median move.
If everything is up 3%, a stock up 4% has moved 1%. The first live run flagged
four Norwegian names on the same day; three of them were just the market.

Routine filings — daily buyback tallies, financial calendars, share capital
notices — are kept out of alerts. They are regulatory and they carry nothing.

## Running it

    python scripts/scan.py      # writes data/signals.json
    python scripts/notify.py    # pushes anything new to Telegram

Alerts need `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as repository secrets.
Without them the scan still runs and prints what it would have sent.

## Honest limits

**Cadence.** GitHub Actions cron is best-effort, not punctual — a scheduled run
can drift 10–20 minutes under load. Fine for "what moved today", useless for
reacting inside a minute. That needs a machine you control.

**No backtest yet.** The thresholds are starting points, not settings known to
work. Until forward returns are measured against the signals it emits, this is
a tool for noticing things, not for acting on them.

## Scheduling

The scan declares a cron, but GitHub's scheduled workflows are best effort.
Observed behaviour on this repo: firings drifting forty minutes or more,
individual hours dropped, and on 2026-08-27 every firing dropped for eighteen
hours while the workflow sat enabled and every prior run showed success.
Nothing is broken in that state, so nothing reports it - the page just goes
stale.

`deploy/` puts the clock somewhere that keeps time. A systemd timer on a VPS
dispatches the workflow hourly across market hours; the scan itself still runs
on GitHub, so `DEEPL_API_KEY` and any other repository secrets stay where they
are and the scan logic is untouched.

    sudo bash deploy/install.sh

The cron stays in the workflow as a fallback: if the VPS is down, best effort
beats nothing. When both fire, the trigger sees a run already in progress and
skips, so the overlap is harmless.
