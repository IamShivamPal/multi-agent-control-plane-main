"""
Agents Package
Multi-agent system for CI/CD automation
"""

__version__ = "1.0.0"

# IMPORTANT: Imports are commented out to prevent eager initialization
# This prevents simulations from running when the package is imported
# Import agents explicitly where needed instead of relying on __init__.py

# Agent modules
# from agents.deploy_agent import DeployAgent
# from agents.issue_detector import IssueDetector
# from agents.auto_heal_agent import AutoHealAgent
# from agents.rl_optimizer import RLOptimizer

__all__ = [
    'DeployAgent',
    'IssueDetector',
    'AutoHealAgent',
    'RLOptimizer',
]
