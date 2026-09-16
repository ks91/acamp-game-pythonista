# acamp-game-pythonista

Pythonista 3 client toolkit for Academy Camp 2026's position game.

## Principles

- One iPad is the exploration device for one team, not an individual tracker.
- Game authority remains on the API server.
- The client can durably queue actions while connectivity is unavailable.
- Team-specific runtime configuration lives in untracked `config.py`.

## Current toolkit

- `toolkit/event_queue.py` provides a small JSON-backed FIFO queue for location samples and actions that must be retried after a connection failure.
- `toolkit/api_client.py` sends authenticated JSON requests with Python's standard HTTPS client.
- `toolkit/check_in.py` retries queued location samples before a new sample after connectivity returns.
- `app.py` is the first Pythonista 3 executable: it obtains one GPS fix and sends it to `/v1/location-samples`.

## Pythonista setup

1. Pull this repository using the team's established Pythonista Git workflow.
2. Copy `config.example.py` to `config.py`.
3. Set only the team-specific values supplied by staff.
4. Never commit or share `config.py`.

The next vertical slice will add HTTPS API delivery and Pythonista location acquisition on top of the queue.
