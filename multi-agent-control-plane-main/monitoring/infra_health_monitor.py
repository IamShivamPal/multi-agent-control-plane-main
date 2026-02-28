#!/usr/bin/env python3
"""
Infrastructure Health Monitor
Logs daily system status to infra_health_log.csv
"""

import os
import csv
import datetime
import psutil
import subprocess
import json
from core.env_config import EnvironmentConfig

class InfraHealthMonitor:
    """Monitors and logs infrastructure health metrics."""
    
    def __init__(self, env='dev'):
        self.env_config = EnvironmentConfig(env)
        self.log_file = self.env_config.get_log_path("infra_health_log.csv")
        self._initialize_log()
    
    def _initialize_log(self):
        """Initialize log file with headers."""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'cpu_percent', 'memory_percent', 'disk_percent',
                    'docker_status', 'containers_running', 'containers_total',
                    'redis_status', 'system_health', 'environment'
                ])
    
    def get_system_metrics(self):
        """Collect system performance metrics."""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent
        }
    
    def check_docker_status(self):
        """Check Docker daemon and container status."""
        try:
            result = subprocess.run(['docker', 'ps', '--format', 'json'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                containers = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        containers.append(json.loads(line))
                
                running = len([c for c in containers if 'Up' in c.get('Status', '')])
                total = len(containers)
                
                return 'healthy', running, total
            else:
                return 'unhealthy', 0, 0
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return 'unavailable', 0, 0
    
    def check_redis_status(self):
        """Check Redis connectivity."""
        try:
            import redis
            r = redis.Redis(
                host=self.env_config.get('redis_host', 'localhost'),
                port=self.env_config.get('redis_port', 6379),
                socket_timeout=5
            )
            r.ping()
            return 'healthy'
        except Exception:
            return 'unhealthy'
    
    def calculate_system_health(self, metrics, docker_status, redis_status):
        """Calculate overall system health score."""
        score = 100
        
        # CPU penalty
        if metrics['cpu_percent'] > 80:
            score -= 20
        elif metrics['cpu_percent'] > 60:
            score -= 10
        
        # Memory penalty
        if metrics['memory_percent'] > 85:
            score -= 20
        elif metrics['memory_percent'] > 70:
            score -= 10
        
        # Disk penalty
        if metrics['disk_percent'] > 90:
            score -= 15
        elif metrics['disk_percent'] > 80:
            score -= 5
        
        # Docker penalty
        if docker_status == 'unhealthy':
            score -= 25
        elif docker_status == 'unavailable':
            score -= 40
        
        # Redis penalty
        if redis_status == 'unhealthy':
            score -= 15
        
        return max(0, score)
    
    def log_health_status(self):
        """Collect and log current health status."""
        timestamp = datetime.datetime.now().isoformat()
        
        # Collect metrics
        metrics = self.get_system_metrics()
        docker_status, containers_running, containers_total = self.check_docker_status()
        redis_status = self.check_redis_status()
        
        # Calculate health score
        health_score = self.calculate_system_health(metrics, docker_status, redis_status)
        
        # Log to CSV
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                round(metrics['cpu_percent'], 2),
                round(metrics['memory_percent'], 2),
                round(metrics['disk_percent'], 2),
                docker_status,
                containers_running,
                containers_total,
                redis_status,
                health_score,
                self.env_config.get('environment')
            ])
        
        print(f"[{self.env_config.get('environment').upper()}] Health logged: {health_score}% "
              f"(CPU: {metrics['cpu_percent']:.1f}%, MEM: {metrics['memory_percent']:.1f}%, "
              f"Docker: {docker_status}, Redis: {redis_status})")
        
        return health_score

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Infrastructure Health Monitor")
    parser.add_argument("--env", choices=['dev', 'stage', 'prod'], default='dev')
    args = parser.parse_args()
    
    monitor = InfraHealthMonitor(args.env)
    health_score = monitor.log_health_status()
    
    # Exit with error code if health is critical
    if health_score < 50:
        exit(1)
    else:
        exit(0)