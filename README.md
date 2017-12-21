# brutus
HTTP/TCP Distributed Computing Framework in Python  
using Amazon Lambda functions

It's simple and it's powerful.

--- 

Working prototype, still under development. 
Not suitable for anything other than exploring, making suggestions/issues.

---

### Requirements  
- Python 3.6 (Lambda is either 2.7 or 3.6)  
  you can attempt to use a different local version, but the lambda version  
  will be Python 3.6
  
- Docker installed with ability to write to this packages location.  
  (Packages are built within a Amazon Linux container, required by Lambda)

---

### Is this package a good fit for you?

Uses Amazon Lambda to distribute workloads  

- Benefits
    - Serverless workers
    - Pay for what you use
    - **Extremely** scalable!
    
- Down sides:
    - Changing local env requires updating remote lambda env
    - Long running functions (> ~3-4 mins) are not suitable
    - Lots of I/O http/tcp traffic
    - I like Anaconda as much as the next guy, but as of now  
      it is not supported. All packages must be `pip` installable.

```python
from brutus import distribute, Client

# max of 1000 simultaneous Lambda functions,
# and ensure local conda env matches remote lambda env
Client(max_workers=1000,
       requirements=['pandas=20.1', 'numpy=1.13']  # or file path to pip freeze file
       )

@distribute
def adder(x):
    time.sleep(random.random())
    return x

@distribute
def times_2(x):
    time.sleep(random.random())
    return x * 2
    
@distribute
def divide(x):
    time.sleep(random.random())
    return x / 2.

results = map(adder, range(5))
results = map(times_2, results)
results = map(divide, results))
```
