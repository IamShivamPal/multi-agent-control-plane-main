from .trace import generate_trace_id

def inject_trace(request: dict):
    if "trace_id" not in request:
        request["trace_id"] = generate_trace_id()
    return request