import requests
import time
import dill



def adder(x, y):
    return x + y



avg = []
for i in range(100):
    start = time.perf_counter()
    msg = dict(job_id='test-{}'.format(i + 1),
               func=adder,
               args=(2, 3 * i),
               kwargs={})

    msg = dill.dumps(msg)


    r = requests.post('http://localhost:5555/submit_job', files={'job': msg})
    avg.append(time.perf_counter() - start)

print(r)
print('AVG response: {}s'.format(sum(avg) / float(len(avg))))
