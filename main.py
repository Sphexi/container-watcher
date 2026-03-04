import time
import re
import docker
import logging
import os
from datetime import datetime, timedelta

# Logging setup — respects LOG_LEVEL env variable (DEBUG, INFO, WARNING, ERROR)
_log_level_name = os.environ.get('LOG_LEVEL', 'INFO').upper()
_log_level = getattr(logging, _log_level_name, logging.INFO)
logging.basicConfig(
    level=_log_level,
    format='%(asctime)s %(levelname)-8s %(name)s: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S')
logger = logging.getLogger('watcher')

# Time between container check cycles (seconds)
CHECK_INTERVAL = 60

# Tracks containers under management:
# {container_name: {'id': str, 'interval': str, 'last_restart': datetime}}
tracked_containers = {}


def parse_duration(s):
    """Parse a human-readable duration string into a timedelta.

    Supported units: w (weeks), d (days), h (hours), m (minutes), s (seconds).
    Examples: '30m', '6h', '7d', '1w2d12h30m'
    """
    pattern = re.compile(r'^(?:(\d+)w)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$')
    m = pattern.match(s.strip())
    if not m or not any(m.groups()):
        raise ValueError(
            f"Invalid duration {s!r}. Expected format like '30m', '6h', '7d', '1w2d12h'.")
    weeks, days, hours, minutes, seconds = (int(v or 0) for v in m.groups())
    return timedelta(weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)


def check_containers(containers):
    """Evaluate each running container and restart those whose interval has elapsed."""
    running_names = set()

    for container in containers:
        name = container.name
        running_names.add(name)
        labels = container.labels

        if labels.get('watcher.autorestart', '').lower() != 'true':
            logger.debug(f'Container {name!r}: watcher.autorestart not set, skipping')
            continue

        interval_str = labels.get('watcher.autorestart.interval')
        if not interval_str:
            logger.warning(
                f'Container {name!r}: watcher.autorestart=true but watcher.autorestart.interval '
                f'is missing, skipping')
            continue

        try:
            interval = parse_duration(interval_str)
        except ValueError as e:
            logger.warning(f'Container {name!r}: {e}')
            continue

        if name not in tracked_containers:
            tracked_containers[name] = {
                'id': container.short_id,
                'interval': interval_str,
                'last_restart': datetime.now(),
            }
            logger.info(f'Container {name!r} ({container.short_id}): tracking started, interval={interval_str}')
            continue

        entry = tracked_containers[name]
        # Update interval if the label changed
        entry['interval'] = interval_str
        last_restart = entry['last_restart']
        elapsed = datetime.now() - last_restart

        if elapsed >= interval:
            logger.info(
                f'Container {name!r} ({entry["id"]}): restarting '
                f'(elapsed={str(elapsed).split(".")[0]}, interval={interval_str})')
            try:
                container.restart()
                entry['last_restart'] = datetime.now()
                logger.info(f'Container {name!r} ({entry["id"]}): restarted successfully')
            except docker.errors.APIError as e:
                logger.error(f'Container {name!r} ({entry["id"]}): restart failed: {e}')
        else:
            remaining = interval - elapsed
            logger.debug(
                f'Container {name!r} ({entry["id"]}): interval not reached '
                f'(elapsed={str(elapsed).split(".")[0]}, '
                f'remaining={str(remaining).split(".")[0]})')

    # Drop containers that are no longer running
    for name in set(tracked_containers) - running_names:
        entry = tracked_containers.pop(name)
        logger.info(f'Container {name!r} ({entry["id"]}): no longer running, removed from tracking')


def main():
    logger.info('Container watcher starting up')

    try:
        client = docker.from_env()
        logger.info('Connected to Docker daemon')
    except docker.errors.DockerException as e:
        logger.error(f'Failed to connect to Docker daemon: {e}')
        raise

    while True:
        logger.debug('Starting check cycle')
        try:
            containers = client.containers.list()
            logger.debug(f'Found {len(containers)} running containers')
            check_containers(containers)
        except docker.errors.DockerException as e:
            logger.error(f'Docker API error during check cycle: {e}')

        if tracked_containers:
            logger.info(f'Tracking {len(tracked_containers)} container(s):')
            for cname, entry in tracked_containers.items():
                next_restart = entry['last_restart'] + parse_duration(entry['interval'])
                logger.info(
                    f'  {cname} ({entry["id"]})  interval={entry["interval"]}'
                    f'  last_restart={entry["last_restart"].strftime("%Y-%m-%dT%H:%M:%S")}'
                    f'  next={next_restart.strftime("%Y-%m-%dT%H:%M:%S")}')
        else:
            logger.info('No containers currently tracked')
        logger.debug(f'Sleeping {CHECK_INTERVAL}s until next check')
        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
