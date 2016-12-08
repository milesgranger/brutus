# brutus
HTTP/TCP Distributed Computing Framework in Python

It's simple and it's powerful.

--- 

Under development.


---

### Intent

Uses a central Flask/Gevent Server which is contacted by hungry worker processes looking for work. 

Goal:

```
from brutus import distribute, Scheduler

scheduler = Scheduler(address=...)

@distribute(scheduler=scheduler)
def some_function():
    ...
```
