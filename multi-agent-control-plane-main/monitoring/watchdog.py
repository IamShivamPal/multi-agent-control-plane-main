#!/usr/bin/env python3
"""
Container Watchdog
Monitors Docker container status and performs auto-restart actions
"""

import os
import time
import subprocess
import json
import datetime
import csv
from core.env_config import EnvironmentConfig

class ContainerWatchdog:
    """Monitors and manages Docker container health."""
    
    def __init__(self, env='dev'):
        self.env_config = EnvironmentConfig(env)
        self.log_file = self.env_config.get_log_path("watchdog_log.csv")
        self.containers = [
            'cicd-dashboard',
            'cicd-mcp', 
            'cicd-agents',
            'cicd-redis'
        ]
        self._initialize_log()
    
    def _initialize_log(self):
        """Initialize watchdog log file."""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'container_name', 'status', 'health', 
                    'action_taken', 'restart_count', 'environment'
                ])
    
    def get_container_status(self, container_name):
        """Get detailed container status."""
        try:
            # Get container info
            result = subprocess.run([
                'docker', 'inspect', container_name
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return None, None, 0
            
            info = json.loads(result.stdout)[0]
            state = info['State']
            
            status = 'running' if state['Running'] else 'stopped'
            health = state.get('Health', {}).get('Status', 'none')
            restart_count = state.get('RestartCount', 0)
            
            return status, health, restart_count
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, 
                json.JSONDecodeError, KeyError, IndexError):
            return None, None, 0
    
    def restart_container(self, container_name):
        """Restart a specific container."""
        try:
            print(f"🔄 Restarting container: {container_name}")
            result = subprocess.run([
                'docker', 'restart', container_name
            ], capture_output=True, text=True, timeout=30)
            
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return False
    
    def start_container(self, container_name):
        """Start a stopped container."""
        try:
            print(f"▶️ Starting container: {container_name}")
            result = subprocess.run([
                'docker', 'start', container_name
            ], capture_output=True, text=True, timeout=30)
            
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return False
    
    def log_action(self, container_name, status, health, action, restart_count):
        """Log watchdog action."""
        timestamp = datetime.datetime.now().isoformat()
        
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp, container_name, status, health, 
                action, restart_count, self.env_config.get('environment')
            ])
    
    def check_and_heal_container(self, container_name):
        """Check container health and take corrective action."""
        status, health, restart_count = self.get_container_status(container_name)
        action_taken = 'none'
        
        if status is None:
            print(f"❌ Container {container_name} not found")
            action_taken = 'not_found'
        
        elif status == 'stopped':
            print(f"🚨 Container {container_name} is stopped")
            if self.start_container(container_name):
                action_taken = 'started'
                print(f"✅ Container {container_name} started successfully")
            else:
                action_taken = 'start_failed'
                print(f"❌ Failed to start container {container_name}")
        
        elif health == 'unhealthy':
            print(f"🚨 Container {container_name} is unhealthy")
            if restart_count < 5:  # Avoid restart loops
                if self.restart_container(container_name):
                    action_taken = 'restarted'
                    print(f"✅ Container {container_name} restarted successfully")
                else:
                    action_taken = 'restart_failed'
                    print(f"❌ Failed to restart container {container_name}")
            else:
                action_taken = 'restart_limit_reached'
                print(f"⚠️ Container {container_name} restart limit reached")
        
        elif status == 'running' and health in ['healthy', 'none']:
            action_taken = 'healthy'
        
        # Log the action
        self.log_action(container_name, status or 'unknown', 
                       health or 'unknown', action_taken, restart_count)
        
        return action_taken
    
    def monitor_all_containers(self):
        """Monitor all configured containers."""
        print(f"🔍 Monitoring containers in {self.env_config.get('environment').upper()} environment...")
        
        actions_summary = {}
        for container in self.containers:
            action = self.check_and_heal_container(container)
            actions_summary[container] = action
        
        return actions_summary
    
    def run_continuous_monitoring(self, interval=60):
        """Run continuous container monitoring."""
        print(f"🚀 Starting continuous monitoring (interval: {interval}s)")
        
        try:
            while True:
                self.monitor_all_containers()
                print(f"⏰ Next check in {interval} seconds...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Container Watchdog")
    parser.add_argument("--env", choices=['dev', 'stage', 'prod'], default='dev')
    parser.add_argument("--continuous", action='store_true', 
                       help='Run continuous monitoring')
    parser.add_argument("--interval", type=int, default=60,
                       help='Monitoring interval in seconds')
    
    args = parser.parse_args()
    
    watchdog = ContainerWatchdog(args.env)
    
    if args.continuous:
        watchdog.run_continuous_monitoring(args.interval)
    else:
        actions = watchdog.monitor_all_containers()
        
        # Exit with error if any critical issues found
        critical_actions = ['start_failed', 'restart_failed', 'not_found']
        if any(action in critical_actions for action in actions.values()):
            exit(1)
        else:
            exit(0)