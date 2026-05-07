from sarathi.headers import SARATHI_HEADER, SARATHI_VALUE

def validate_caller(headers: dict):
    caller = headers.get(SARATHI_HEADER)

    if caller != SARATHI_VALUE:
        print(f"[X-CALLER={caller or 'missing'}] rejected: 403")
        raise PermissionError("403 Forbidden: Only Sarathi can call Executer")

    print(f"[X-CALLER={SARATHI_VALUE}] accepted")