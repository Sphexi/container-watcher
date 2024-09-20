# This Python script will run as an application inside of a Docker Container and
# is meant to watch the Docker daemon for the status of all running containers.
# You can configure other containers with env variables that will be used by
# this script to determine:
# - The container name
# - If it should be restarted or not
# - How often in-between restarts (ie 05:00:00 for 5 hours, 00:30:00 for 30 minutes, etc) 
# It's meant to be a CRON job of sorts for rebooting Docker containers in situations
# where the containers are running some sort of service that doesn't do a health check
# and would benefit from a regular restart.

# The env variables that you set on the other containers will determine the conditions 
# for restarting those containers.

# The script will run every 60 seconds, so if you want to restart a container every
# 5 hours, you would set the RESTART_INTERVAL variable to 05:00:00. The script will
# then check the current time against the last restart time and restart the container
# if the interval has been reached.
# 
# To run the script, you would build it into a Docker container and run it with the
# following command:
# docker run -d --name container-watcher --restart=always -v /var/run/docker.sock:/var/run/docker.sock container-watcher
# 
# The script will then run inside of the container and watch the Docker
# daemon for containers that need to be restarted. If a container needs to be restarted,
# the script will restart it and update the last restart time. The script will then
# continue to run and check for other containers that need to be restarted.

import time
import docker
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the array to store the container names and the last time they were restarted
container_array = []
restart_container = False
restart_interval = None

# Get the Docker client
client = docker.from_env()

# Get a list of running containers from the Docker daemon
def get_running_containers():
    containers = client.containers.list()
    return containers

# Loop through the list of containers and look at the env variables
def check_containers(containers):
    for docker_container in containers:
        restart_container = False
        restart_interval = None

        container_name = docker_container.name
        container_env = docker_container.attrs['Config']['Env']
        for env in container_env:
            if 'RESTART_CONTAINER' in env:
                restart_container = env.split('=')[1]
                logger.info(f'Container: {container_name}, Restart: {restart_container}')
            if 'RESTART_INTERVAL' in env:
                restart_interval = datetime.strptime(env.split('=')[1], "%H:%M:%S")
                logger.info(f'Container: {container_name}, Restart Interval: {restart_interval}')
        
        # Check if the container should be restarted, and maintain the array of watched containers
        if restart_container == True:
            logger.info(f'Container: {container_name}, Restart: {restart_container}, Restart Interval: {restart_interval}')
            if container_name not in container_array:
                container_array.append({'name': container_name, 'last_restart': datetime.now()})
            else:
                for container in container_array:
                    if container['name'] == container_name:
                        last_restart = container['last_restart']
                        now = datetime.now()
                        interval = datetime.strptime(str(now - last_restart), "%H:%M:%S.%f")
                        if interval > restart_interval:
                            logger.info(f'Restarting container: {container_name}')
                            docker_container.restart()
                            container['last_restart'] = datetime.now()
                            logger.info(f'Container: {container_name} has been restarted')
                        else:
                            logger.info(f'Container: {container_name} has not reached the restart interval yet. Exiting...')

# Main loop
def main():
    while True:
        logger.info('Checking for containers that need to be restarted...')
        containers = get_running_containers()
        logger.info('Containers to check...')
        logger.info(containers)
        check_containers(containers)
        logger.info('List of tracked containers:')
        logger.info(container_array)
        logger.info('Sleeping for 60 seconds...')
        time.sleep(60)

if __name__ == '__main__':
    main()