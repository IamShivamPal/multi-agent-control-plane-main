#!/usr/bin/env python3
"""
System Health Check
Comprehensive health monitoring combining infrastructure and container health
"""

import os
import sys
import datetime
import csv
from infra_health_monitor import InfraHealthMonitor
from watchdog import ContainerWatchdog
from core.env_config import EnvironmentConfig

class SystemHealthCheck:
    """Comprehensive system health checker."""
    
    def __init__(self, env='dev'):
        self.env_config = EnvironmentConfig(env)
        self.infra_monitor = InfraHealthMonitor(env)
        self.watchdog = ContainerWatchdog(env)
        self.log_file = self.env_config.get_log_path("system_health_check.csv")
        self._initialize_log()
    
    def _initialize_log(self):
        """Initialize system health log."""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'infra_health_score', 'containers_healthy',
                    'containers_total', 'overall_status', 'critical_issues',
                    'recommendations', 'environment'
                ])
    
    def run_comprehensive_check(self):
        """Run comprehensive system health check."""
        print(f"🏥 Running comprehensive health check for {self.env_config.get('environment').upper()}...")
        
        # Infrastructure health
        infra_score = self.infra_monitor.log_health_status()
        
        # Container health
        container_actions = self.watchdog.monitor_all_containers()
        
        # Analyze container health
        healthy_containers = sum(1 for action in container_actions.values() 
                               if action in ['healthy', 'started', 'restarted'])
        total_containers = len(container_actions)
        
        # Determine overall status
        critical_issues = []
        recommendations = []
        
        if infra_score < 50:
            critical_issues.append('low_infra_health')
            recommendations.append('check_system_resources')
        
        if healthy_containers < total_containers:
            critical_issues.append('container_issues')
            recommendations.append('check_container_logs')
        
        failed_actions = [name for name, action in container_actions.items() 
                         if action in ['start_failed', 'restart_failed', 'not_found']]
        if failed_actions:
            critical_issues.append(f'failed_containers:{len(failed_actions)}')\n            recommendations.append('manual_intervention_required')\n        \n        # Overall status\n        if not critical_issues:\n            overall_status = 'healthy'\n        elif len(critical_issues) == 1 and infra_score > 70:\n            overall_status = 'warning'\n        else:\n            overall_status = 'critical'\n        \n        # Log results\n        timestamp = datetime.datetime.now().isoformat()\n        with open(self.log_file, 'a', newline='') as f:\n            writer = csv.writer(f)\n            writer.writerow([\n                timestamp,\n                infra_score,\n                healthy_containers,\n                total_containers,\n                overall_status,\n                ';'.join(critical_issues) if critical_issues else 'none',\n                ';'.join(recommendations) if recommendations else 'none',\n                self.env_config.get('environment')\n            ])\n        \n        # Print summary\n        print(f\"\\n📊 Health Check Summary:\")\n        print(f\"   Infrastructure Health: {infra_score}%\")\n        print(f\"   Containers Healthy: {healthy_containers}/{total_containers}\")\n        print(f\"   Overall Status: {overall_status.upper()}\")\n        \n        if critical_issues:\n            print(f\"   ⚠️ Critical Issues: {', '.join(critical_issues)}\")\n        \n        if recommendations:\n            print(f\"   💡 Recommendations: {', '.join(recommendations)}\")\n        \n        return overall_status, infra_score, healthy_containers, total_containers\n\nif __name__ == \"__main__\":\n    import argparse\n    \n    parser = argparse.ArgumentParser(description=\"System Health Check\")\n    parser.add_argument(\"--env\", choices=['dev', 'stage', 'prod'], default='dev')\n    parser.add_argument(\"--fail-on-warning\", action='store_true',\n                       help='Exit with error code on warning status')\n    \n    args = parser.parse_args()\n    \n    health_checker = SystemHealthCheck(args.env)\n    status, infra_score, healthy, total = health_checker.run_comprehensive_check()\n    \n    # Exit codes\n    if status == 'critical':\n        sys.exit(2)\n    elif status == 'warning' and args.fail_on_warning:\n        sys.exit(1)\n    else:\n        sys.exit(0)