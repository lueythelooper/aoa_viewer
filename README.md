# Angle of Arrival Service

Receives UDP CSV packets (`udp_timestamp,azimuth_deg,elevation_deg`) on
`0.0.0.0:5005` and visualizes the angle of arrival to a platform in 3D,
served on `http://0.0.0.0:8000`.

## Run

```bash
pip install -r requirements.txt
python server.py
```

Then open http://localhost:8000 in a browser.

## Test without hardware

In a second terminal:

```bash
python test_sender.py
```

This streams a sweeping azimuth/elevation pattern to `127.0.0.1:5005`.

## Data format

Each UDP packet is a CSV line:

```
<udp_timestamp>,<azimuth_deg>,<elevation_deg>[,<beam_width_deg>]
```

- `udp_timestamp`: numeric timestamp (e.g. seconds since epoch), passed through as-is
- `azimuth_deg`: 0-360, clockwise from North
- `elevation_deg`: degrees above (+) or below (-) the horizon
- `beam_width_deg` (optional, not yet produced by any real source): full
  angular width of the beam cone. When absent, the UI falls back to a fixed
  3° default. `test_sender.py` does not send this field yet.

## Layout

- Left sidebar: reserved status panel, intentionally left blank for future
  system status/telemetry (see `#status-body` in `static/index.html`).
- Main panel: live 3D view (Three.js) — a translucent cone (beam) whose
  apex sits at the platform (teal sphere at origin) and opens outward
  along the received azimuth/elevation direction, 3° wide by default, with
  a numeric readout (azimuth, elevation, beam width, timestamp, link age,
  source) overlaid top-left. A labeled "N" post on the compass ring marks
  azimuth 0 as a fixed north reference while orbiting.
