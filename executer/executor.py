import uuid

def attach_execution_id(signal: dict):
    if not signal.get("execution_id"):
        signal["execution_id"] = str(uuid.uuid4())
    signal["source"] = "executer"
    return signal