import threading ## i/o 
import time

start = time.perf_counter()

def something():
    print('Something was called')
    time.sleep(1)
    print('time was called within something')

threads = list()

for _ in range(100):
    t = threading.Thread(target=something)
    t.start()
    threads.append(t)

for thread in threads:
    thread.join()

finish = time.perf_counter()

print(f'Finished in time: {round(finish - start, 6)} seconds')

