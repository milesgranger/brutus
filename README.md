# brutus
HTTP/TCP Distributed and Persisted Computing Framework in Python

It's simple and it's powerful.

--- 

Working prototype, still under active development. 
Not suitable for anything other than exploring, making suggestions/issues.

---

### Use

Uses a central Flask/Gevent Server which is contacted by hungry worker processes looking for jobs.
Functions and their args/kwargs are stored in a sqlite database on the scheduler, and when worker processes contact server
they are given a job. 

```
from brutus import distribute, wait

# Assuming localhost:4541 scheduler..
@distribute
def adder(x):
    time.sleep(random.random())
    return x

@distribute
def times_2(x):
    time.sleep(random.random())
    return x * 2
    
# Use different scheduler
@distribute(address='some_ip_address:4541')
def divide(x):
    time.sleep(random.random())
    return x / 2.

results = map(adder, range(5))
results = map(times_2, results)
results = wait(map(divide, results))
```
