#!/usr/bin/env python3
"""Policy-Based Container Watchdog with Auto-Restart"""
import subprocess
import time
import csv
import os
from datetime import datetime
from core.env_config import EnvironmentConfig

class ContainerWatchdog:
    """Monitors container health and enforces restart policies."""
    
    def __init__(self, env='dev'):
        self.env = env
        self.env_config = EnvironmentConfig(env)
        self.log_file = self.env_config.get_log_path('watchdog_log.csv')
        self.restart_policy = {
            'max_failures': 3,
            'restart_delay': 30,
            'health_check_interval': 60
        }
        self.failure_counts = {}
        self._initialize_log()
    
    def _initialize_log(self):
        if not os.path.exists(self.log_file):
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'container', 'status', 'action', 'failure_count'])
    
    def check_container_health(self, container_name):
        """Check container health and enforce restart policy."""
        try:
            result = subprocess.run(['docker', 'inspect', '--format={{.State.Health.Status}}', container_name], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                health_status = result.stdout.strip()
                if health_status == 'unhealthy':
                    return self._handle_unhealthy_container(container_name)
                else:
                    self._reset_failure_count(container_name)
                    return 'healthy'
            else:
                return self._handle_container_not_found(container_name)
                
        except subprocess.TimeoutExpired:
            return self._handle_unhealthy_container(container_name, 'timeout')
        except Exception as e:
            self._log_action(container_name, 'error', f'check_failed: {e}', 0)
            return 'error'
    
    def _handle_unhealthy_container(self, container_name, reason='unhealthy'):
        """Handle unhealthy container with restart policy."""
        self.failure_counts[container_name] = self.failure_counts.get(container_name, 0) + 1
        failure_count = self.failure_counts[container_name]
        
        if failure_count <= self.restart_policy['max_failures']:
            self._restart_container(container_name)
            self._log_action(container_name, reason, 'restarted', failure_count)
            return 'restarted'
        else:
            self._log_action(container_name, reason, 'max_failures_reached', failure_count)
            return 'failed'
    
    def _restart_container(self, container_name):
        """Restart container with policy delay."""
        try:
            subprocess.run(['docker', 'restart', container_name], check=True, timeout=30)
            time.sleep(self.restart_policy['restart_delay'])
        except Exception as e:
            self._log_action(container_name, 'restart_failed', str(e), 0)
    
    def _reset_failure_count(self, container_name):
        """Reset failure count on healthy status."""
        if container_name in self.failure_counts:
            del self.failure_counts[container_name]
    
    def _handle_container_not_found(self, container_name):
        """Handle container not found scenario."""
        self._log_action(container_name, 'not_found', 'container_missing', 0)
        return 'not_found'
    
    def _log_action(self, container, status, action, failure_count):
        """Log watchdog actions."""
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().isoformat(), container, status, action, failure_count])

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=['dev', 'stage', 'prod'], default='dev')
    parser.add_argument("--containers", nargs='+', default=['cicd-dashboard', 'cicd-agents'])
    args = parser.parse_args()
    
    watchdog = ContainerWatchdog(args.env)
    
    while True:
        for container in args.containers:
            status = watchdog.check_container_health(container)
            print(f"[{args.env.upper()}] {container}: {status}")
        
        time.sleep(watchdog.restart_policy['health_check_interval'])