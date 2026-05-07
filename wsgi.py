"""
Render-Safe Entry Point for Agent API
Ensures Flask server starts before agent loop initialization.
"""

import os
import sys

# Add project root to path
root_dir = os.path.abspath(os.path.dirname(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import the Flask app (this will initialize the agent in background)
from api.agent_api import app

# Gunicorn will import this module and use the 'app' object
# The agent thread starts automatically when agent_api is imported

if __name__ == '__main__':
    # This block only runs for local development
    port = int(os.getenv('CONTROL_PLANE_PORT', os.getenv('PORT', 7000)))
    print(f"Starting Agent API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
