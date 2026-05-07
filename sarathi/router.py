from .headers import SARATHI_HEADER, SARATHI_VALUE

def attach_sarathi_header(headers: dict):
    headers[SARATHI_HEADER] = SARATHI_VALUE
    print(f"[X-CALLER={SARATHI_VALUE}] accepted")
    return headers