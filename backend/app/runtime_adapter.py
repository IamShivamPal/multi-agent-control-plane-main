from monitoring.runtime_poller import RuntimePoller
from .decision_engine import DecisionEngine
from .schemas import DecisionRequest, Environment, EventType


def map_runtime_to_decision(runtime_payload: dict) -> DecisionRequest:
    """
    Convert runtime payload into DecisionRequest contract.
    """

    env_map = {
        "dev": Environment.DEV,
        "stage": Environment.STAGE,
        "prod": Environment.PROD,
    }

    # Determine event type
    if runtime_payload["latency_ms"] > 2000:
        event_type = EventType.LATENCY
    elif runtime_payload["state"] != "running":
        event_type = EventType.HIGH_MEMORY  # temporary mapping
    else:
        event_type = EventType.HIGH_CPU  # default fallback

    # Fake CPU/memory for now (we will improve later)
    cpu = 70 if runtime_payload["state"] != "running" else 30
    memory = 75 if runtime_payload["errors_last_min"] > 0 else 40

    return DecisionRequest(
        environment=env_map.get(runtime_payload["env"].lower(), Environment.DEV),
        event_type=event_type,
        cpu=cpu,
        memory=memory,
    )


def runtime_decision_cycle(service_name: str, base_url: str):
    """
    One full runtime → decision integration test.
    """
    poller = RuntimePoller(env="dev")

    poll_result = poller.poll_service(service_name, base_url)
    runtime_payload = poller.build_runtime_payload(poll_result)

    decision_request = map_runtime_to_decision(runtime_payload)
    decision = DecisionEngine.decide(decision_request)

    return {
        "runtime_payload": runtime_payload,
        "decision": decision,
    }