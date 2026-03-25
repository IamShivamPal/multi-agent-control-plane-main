from flask import Flask, render_template, jsonify
import time
from decision_engine import DecisionEngine
from runtime_contract import RuntimeState
import random
import os
import json

from flask import request, jsonify
from decision_engine import DecisionEngine
from runtime_contract import RuntimeState
from flask import request







from flask_cors import CORS








app = Flask(__name__)
engine = DecisionEngine()
CORS(app)

APPS = ['app-web', 'app-api', 'app-db']
def generate_initial_data():
    print("=== Generating initial data ===")
    for i in range(5):
        for app_id in APPS:
            state = RuntimeState(
                app_id=app_id,
                current_replicas=random.randint(2, 5),
                desired_replicas=3,
                cpu_usage=random.uniform(0.3, 0.95),
                memory_usage=random.uniform(0.3, 0.9),
                error_rate=random.uniform(0.0, 0.05),
                latency_p99=random.uniform(200, 800),
                last_deployment_time=time.time() - 3600,
                signals=[],
                environment='prod'
            )
            result = engine.process_runtime_state(state)
            print(f"Generated decision for {app_id}: {result['action_emitted']}")
    print("=== Initial data generated ===")

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/test')
def test():
    return jsonify({'status': 'ok', 'message': 'API is working'})

@app.route('/api/stats')
def get_stats():
    try:
        all_stats = engine.app_state_manager.get_all_apps_stats()
        
        total_decisions = 0
        successful = 0
        failed = 0
        
        for stat in all_stats:
            if stat:
                total_decisions += stat.get('total_decisions', 0)
                successful += stat.get('successful_decisions', 0)
                failed += stat.get('failed_decisions', 0)
        
        success_rate = (successful / total_decisions * 100) if total_decisions > 0 else 0
        active_apps = len([s for s in all_stats if s and s.get('total_decisions', 0) > 0])
        
        result = {
            'total_apps': len(APPS),
            'total_decisions': total_decisions,
            'successful_decisions': successful,
            'failed_decisions': failed,
            'success_rate': round(success_rate, 2),
            'active_apps': active_apps
        }
        
        print(f"Stats API called: {result}")
        return jsonify(result)
        
    except Exception as e:
        print(f"ERROR in get_stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/apps')
def get_apps():
    try:
        apps_data = []
        
        for app_id in APPS:
            state = RuntimeState(
                app_id=app_id,
                current_replicas=random.randint(2, 5),
                desired_replicas=3,
                cpu_usage=random.uniform(0.3, 0.95),
                memory_usage=random.uniform(0.3, 0.9),
                error_rate=random.uniform(0.0, 0.05),
                latency_p99=random.uniform(200, 800),
                last_deployment_time=time.time() - 3600,
                signals=[],
                environment='prod'
            )
            
            decision = engine.process_runtime_state(state)
            stats = engine.app_state_manager.get_app_stats(app_id)
            
            app_data = {
                'app_id': app_id,
                'cpu': round(state.cpu_usage * 100, 1),
                'memory': round(state.memory_usage * 100, 1),
                'error_rate': round(state.error_rate * 100, 2),
                'latency': round(state.latency_p99, 0),
                'replicas': state.current_replicas,
                'last_decision': decision.get('action_emitted', 'noop'),
                'total_decisions': stats['total_decisions'] if stats else 0,
                'success_rate': 0
            }
            
            if stats and stats['total_decisions'] > 0:
                app_data['success_rate'] = round((stats['successful_decisions'] / stats['total_decisions'] * 100), 1)
            
            apps_data.append(app_data)
        
        print(f"Apps API called: {len(apps_data)} apps")
        return jsonify(apps_data)
        
    except Exception as e:
        print(f"ERROR in get_apps: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/decisions')
def get_decisions():
    try:
        logs = engine.get_decision_logs(limit=15)
        
        decisions = []
        for log in logs:
            decisions.append({
                'decision_id': log['decision_id'][:8],
                'app_id': log['app_id'],
                'action': log['action_emitted'],
                'enforced': log['action_requested'] != log['action_emitted'],
                'acknowledged': log.get('orchestrator_acknowledged', False),
                'timestamp': log['timestamp']
            })
        
        print(f"Decisions API called: {len(decisions)} decisions")
        return jsonify(decisions)
        
    except Exception as e:
        print(f"ERROR in get_decisions: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    

    
engine = DecisionEngine()

# @app.route("/process-runtime", methods=["POST"])
# def process_runtime():
#     data = request.json

#     result = engine.process_runtime_state(
#         RuntimeState(**data)
#     )

#     return jsonify(result)


# @app.route("/process-runtime", methods=["POST"])
# def process_runtime():
#     data = request.json

#     print("RECEIVED:", data)

#     return {
#         "action_requested": "restart",
#         "confidence": 1.0,
#         "reason": "crash_detected"
#     }

@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.json
    print("FEEDBACK RECEIVED:", data)
    return {"status": "received"}

# @app.route("/process-runtime", methods=["GET", "POST"])
# def process_runtime():
#     if request.method == "GET":
#         return {"message": "Use POST for decision"}

#     data = request.json
#     return {
#         "action_requested": "restart",
#         "confidence": 1.0,
#         "reason": "crash_detected"
#     }



@app.route("/process-runtime", methods=["POST"])
def process_runtime():
    data = request.json

    print("RECEIVED:", data)

    return jsonify({
        "action_requested": "restart",
        "confidence": 1.0,
        "reason": "crash_detected"
    })



# @app.route("/execute-action", methods=["POST"])
# def execute_action():
#     data = request.json

#     action = data.get("action")
#     app_id = data.get("app_id")

#     print(f"EXECUTING: {action} on {app_id}")
#     print("RECEIVED ACTION:", action)

#     # 🔥 SIMULATED EXECUTION (for now)
#     if action == "restart":
#         return jsonify({
#             "status": "success",
#             "message": f"{app_id} restarted"
#         })

#     elif action == "scale_up":
#         return jsonify({
#             "status": "success",
#             "message": f"{app_id} scaled up"
#         })

#     return jsonify({
#         "status": "noop",
#         "message": "No action taken"
#     })



@app.route("/execute-action", methods=["POST"])
def execute_action():
    data = request.json

    action = data.get("action")
    app_id = data.get("app_id")

    # 🔥 ADD THIS LINE HERE
    print("RECEIVED ACTION:", action)

    print(f"EXECUTING: {action} on {app_id}")

    if action == "restart":
        return jsonify({
            "message": f"{app_id} restarted",
            "success": True
        })

    elif action == "scale_up":
        return jsonify({
            "status": "success",
            "message": f"{app_id} scaled up"
        })

    return jsonify({
        "status": "noop",
        "message": "No action taken"
    })






# LOG_FILE = "logs/dev/rl_execution_feedback.jsonl"
LOG_FILE = r"C:\Users\spal4\Desktop\SHIVAM\BHIV\multi-agent-control-plane-main\logs\dev\rl_execution_feedback.jsonl"

# @app.route("/api/runtime-metrics", methods=["GET"])
# def runtime_metrics():
#     if not os.path.exists(LOG_FILE):
#         return jsonify([])

#     data = []

#     with open(LOG_FILE, "r") as f:
#         for line in f:
#             try:
#                 data.append(json.loads(line))
#             except:
#                 continue

#     return jsonify(data[-50:])

@app.route("/api/runtime-metrics")
def get_metrics():
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()

        data = [json.loads(line) for line in lines if line.strip()]
        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == '__main__':
    generate_initial_data()
    print("\n=== Starting Flask server ===")
    print("Dashboard: http://localhost:5000")
    app.run(debug=True, port=5000, use_reloader=False)
