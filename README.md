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

### Standard iPad workflow: Working Copy owns Git, Pythonista runs the linked folder

Use [Working Copy](https://workingcopyapp.com/) as the sole Git client on each iPad. Pythonista supports editing entire folders from other apps in place, including Git repositories from Working Copy ([Pythonista documentation](https://omz-software.com/pythonista/docs-3.4/py3/ios/pythonista.html)).

1. In Working Copy, tap **+** and clone `https://github.com/ks91/acamp-game-pythonista.git`.
2. In Pythonista, use its Files / external-folder integration to open that **entire Working Copy repository folder** and run `app.py` there.
3. If the iPad does not expose the Working Copy folder directly, create a shared folder in the Files app (for example `iCloud Drive/Pythonista/acamp-game-pythonista`) and use Working Copy's **Link Repository** / folder-link integration for that folder. Do **not** use Pythonista's sandboxed `This iPad` folder as the Git working folder: Working Copy cannot update it in place.
4. For every update: use **Pull** in Working Copy, completely quit and reopen Pythonista, then run `app.py` from the same linked folder.
5. Never update only `app.py`: the toolkit files and `app.py` must always come from the same commit.

### Team-specific configuration

1. Copy `config.example.py` to `config.py` in the linked repository.
2. Set only the team-specific values supplied by staff.
3. Never commit or share `config.py`.

`app.py` calls `make_location_sample(..., sample_id=...)`. If Pythonista reports a missing `sample_id` keyword-only argument, `app.py` and `toolkit/location_payload.py` came from different commits. Pull the complete repository in Working Copy and make sure Pythonista is running the linked repository—not an older copied folder.

The next vertical slice will add team-state display on top of the check-in flow.
