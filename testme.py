from datetime import datetime
from time import sleep

interval = datetime.strptime("00:00:12", "%H:%M:%S")
start = datetime.now()
print(start)
sleep(10)
end = datetime.now()
print(end)
duration = end - start

print(duration)
duration = datetime.strptime(str(duration), "%H:%M:%S.%f")
if duration > interval:
    print("Time to restart the container")