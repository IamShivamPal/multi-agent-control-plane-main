from agent_runtime import AgentRuntime

agent = AgentRuntime(env="dev")

event = {
    "event_type": "crash",
    "app_id": "app1",
    "cpu_percent": 95,
    "memory_percent": 80,
    "workers": 2
}

result = agent.handle_external_event(event)
print(result)