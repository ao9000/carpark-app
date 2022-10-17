import functools
import json
import time
from app.exceptions import APIUnavailableError


# API handlers
def retry_API(num=3):
    def decorator(func):
        @functools.wraps(func)
        def func_wrapper(*args, **kwargs):
            for i in range(num):
                request = func(*args, **kwargs)
                if request.status_code == 200:
                    return json.loads(request.text)
                else:
                    if i == (num-1):
                        # Last retry
                        raise APIUnavailableError(func.__name__, request.status_code)
                    print(f"[{i+1}/{num}] API error: {request.status_code}, retrying after 3 seconds...")
                    time.sleep(3)

        return func_wrapper

    return decorator
