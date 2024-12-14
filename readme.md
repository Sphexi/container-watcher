# Docker Container Watcher

## Overview
The problem I had was that I had a number of services running inside of Docker containers that would occassionally fall over.  These services were themselves sort of hacks, so didn't really have good healthchecks to hook in to and use to recover from, so I needed a different solution.

This project is basically that.  The idea is that it runs as a container itself on the same host, and scans all other containers looking for env variables that tell it what to do.  If it finds containers with the appropriate env variables then it will restart them based on the time specified and log the restart.

It's admittedly a not great solution to a not great problem that all might be better if I just put effort into fixing the root cause of no healthchecks, but it was a quick fix and over several months has worked basically perfectly.

## Implementation
This Python script will run as an application inside of a Docker Container and is meant to watch the Docker daemon for the status of all running containers. You can configure other containers with environment variables that will be used by this script to determine:
- The container name
- If it should be restarted or not
- How often in-between restarts (e.g., 05:00:00 for 5 hours, 00:30:00 for 30 minutes, etc.)

In order to track and restart a container you need to set two environment variables:
- `RESTART_CONTAINER` needs to be set to `true`
- `RESTART_INTERVAL` needs to be set to a time in the format of `HH:MM:SS` in 24-hour time format, ie `05:00:00` or `22:00:00` to restart every five and twenty-two hours

The script will run every 60 seconds, and if you want to restart a container every 5 hours, you would set the `RESTART_INTERVAL` variable to `05:00:00`. The script will then check the current time against the last restart time and restart the container if the interval has been reached. You can set a maximum of `24:00:00` for the interval.

## Deploying the service

To deploy the service in a container, you can use the following command:

```sh
docker run -d --name container-watcher --restart=always -v /var/run/docker.sock:/var/run/docker.sock container-watcher ghcr.io/sphexi/container-watcher:main
```

Alternatively (and arguably better) use the `dockercompose.yaml` to manage the container:

```sh
# download the dockercompose.yaml
curl -o https://raw.githubusercontent.com/Sphexi/container-watcher/refs/heads/main/dockercompose.yaml dockercompose.yaml

# launch the container
docker compose -f dockercompose.yaml up -d
```
If you want to customize the compose file just save it locally and run the `up` command against it.

## Future plans
I am thinking through a couple of options for updates in the future, such as:
- Static time of day based restarts, such as every day at midnight (instead of every x amount of time); certain services I want to restart at a specific time 
- Better logging, something that's more clean in order to pipe out to syslog or a third party tool for tracking
- Probably should use labels instead of environment variables