# Docker Container Watcher

## Overview
The problem I had was that I had a number of services running inside of Docker containers that would occasionally fall over. These services were themselves sort of hacks, so didn't really have good healthchecks to hook in to and use to recover from, so I needed a different solution.

This project is basically that. The idea is that it runs as a container itself on the same host, and scans all other containers looking for labels that tell it what to do. If it finds containers with the appropriate labels then it will restart them based on the interval specified and log the restart.

It's admittedly a not great solution to a not great problem that all might be better if I just put effort into fixing the root cause of no healthchecks, but it was a quick fix and over several months has worked basically perfectly.

## Implementation
This Python script runs as an application inside a Docker container and watches the Docker daemon for running containers. You configure target containers using Docker labels to determine:
- Whether the container should be auto-restarted
- How often it should be restarted

In order to track and restart a container, set these labels on it:
- `watcher.autorestart` — set to `true` to enable
- `watcher.autorestart.interval` — how often to restart, using a human-readable duration string

### Duration format
Durations are expressed as a combination of weeks, days, hours, minutes, and seconds:

| Unit | Symbol | Example |
|------|--------|---------|
| Weeks | `w` | `2w` |
| Days | `d` | `7d` |
| Hours | `h` | `6h` |
| Minutes | `m` | `30m` |
| Seconds | `s` | `90s` |

Units can be combined: `1w2d12h30m`. Intervals longer than 24 hours are fully supported.

### Examples
| Label value | Meaning |
|-------------|---------|
| `30m` | Every 30 minutes |
| `6h` | Every 6 hours |
| `7d` | Every 7 days |
| `1w2d` | Every 9 days |
| `12h30m` | Every 12.5 hours |

### Log levels
Set the `LOG_LEVEL` environment variable on the watcher container to control verbosity:
- `INFO` (default) — restarts, tracking changes, warnings
- `DEBUG` — includes per-cycle details for every container checked
- `WARNING` — only warnings and errors
- `ERROR` — only errors

## Deploying the service

### Docker Compose (recommended)
Download the `dockercompose.yaml` and launch:

```sh
curl -o dockercompose.yaml https://raw.githubusercontent.com/Sphexi/container-watcher/refs/heads/main/dockercompose.yaml

docker compose -f dockercompose.yaml up -d
```

### Docker CLI
```sh
docker run -d \
  --name container-watcher \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  ghcr.io/sphexi/container-watcher:main
```

## Configuring target containers
Add labels to any container you want the watcher to manage. In Docker Compose:

```yaml
services:
  my-service:
    image: my-image
    labels:
      watcher.autorestart: "true"
      watcher.autorestart.interval: "6h"
```

Or via the CLI:
```sh
docker run -d \
  --label watcher.autorestart=true \
  --label watcher.autorestart.interval=6h \
  my-image
```
