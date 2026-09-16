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

### Use Working Copy as the Git client

Use [Working Copy](https://workingcopyapp.com/) to clone and pull this public repository on each iPad. Pythonista supports editing entire folders from other apps in place, including Git repositories from Working Copy ([Pythonista documentation](https://omz-software.com/pythonista/docs-3.4/py3/ios/pythonista.html)). Open and run this repository as a **linked Working Copy folder** in Pythonista; do not copy individual files into a separate Pythonista folder.

1. In Working Copy, clone `https://github.com/ks91/acamp-game-pythonista.git`.
2. Link/open that whole repository folder in Pythonista and run `app.py` from that linked folder.
3. For every update, use **Pull** in Working Copy, then return to the same linked folder in Pythonista.
4. Never update only `app.py`: the toolkit files and `app.py` must always come from the same commit.

### Team-specific configuration

1. Copy `config.example.py` to `config.py` in the linked repository.
2. Set only the team-specific values supplied by staff.
3. Never commit or share `config.py`.

`app.py` calls `make_location_sample(..., sample_id=...)`. If Pythonista reports a missing `sample_id` keyword-only argument, `app.py` and `toolkit/location_payload.py` came from different commits. Pull the complete repository in Working Copy and make sure Pythonista is running the linked repository—not an older copied folder.

The next vertical slice will add team-state display on top of the check-in flow.
