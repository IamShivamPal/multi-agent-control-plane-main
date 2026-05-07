from executer.executor import attach_execution_id
from executer.guard import validate_caller
from pravah_stream.stream import emit

def execute(signal: dict, headers: dict):
    # [SECURITY] enforce caller
    validate_caller(headers)

    # [OK] attach execution_id
    signal = attach_execution_id(signal)

    # [OK] simulate execution (replace later with real logic)
    signal["status"] = "success"

    # [EMIT] emit to pravah
    emit(signal)
    print("[EXECUTER] EXECUTER CALLED")
    return signal