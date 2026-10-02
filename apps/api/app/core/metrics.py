from prometheus_client import Counter, Histogram

REQUESTS=Counter("lys_api_requests_total","Tổng request API",["method","route","status"])
LATENCY=Histogram("lys_api_request_seconds","Độ trễ request API",["method","route"],buckets=(.01,.05,.1,.25,.5,1,2,5,10))
NLP_FAILURES=Counter("lys_nlp_failures_total","Lỗi suy luận NLP",["backend"])
