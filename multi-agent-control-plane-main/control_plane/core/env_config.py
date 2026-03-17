import os


def _parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}

class EnvironmentConfig:
    """Loads environment-specific configuration."""
    
    def __init__(self, env='dev'):
        self.env = env
        self.config = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment file."""
        env_file = os.path.join("environments", f"{self.env}.env")
        if os.path.exists(env_file):
            self._load_env_file(env_file)
    
    def _load_env_file(self, env_file):
        """Simple .env file parser."""
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
            
        # Load all environment variables
        self.config = {
            'environment': os.getenv('ENVIRONMENT', self.env),
            'debug': os.getenv('DEBUG', 'false').lower() == 'true',
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'db_host': os.getenv('DB_HOST', 'localhost'),
            'db_port': int(os.getenv('DB_PORT', 5432)),
            'redis_host': os.getenv('REDIS_HOST', 'localhost'),
            'redis_port': int(os.getenv('REDIS_PORT', 6379)),
            'redis_db': int(os.getenv('REDIS_DB', 0)),
            'deployment_timeout': int(os.getenv('DEPLOYMENT_TIMEOUT', 30)),
            'retry_count': int(os.getenv('RETRY_COUNT', 3)),
            'latency_ms': int(os.getenv('LATENCY_THRESHOLD_MS', 16000)),
            'low_score_avg': int(os.getenv('LOW_SCORE_THRESHOLD', 40)),
            'high_heart_rate': int(os.getenv('HIGH_HEART_RATE', 120)),
            'low_oxygen_level': int(os.getenv('LOW_OXYGEN_LEVEL', 95)),
            'dashboard_port': int(os.getenv('DASHBOARD_PORT', 8501)),
            'autonomy_decisions_enabled': _parse_bool(
                os.getenv('AUTONOMY_DECISIONS_ENABLED'),
                default=True
            ),
            'autonomy_learning_enabled': _parse_bool(
                os.getenv('AUTONOMY_LEARNING_ENABLED'),
                default=self.env == 'dev'
            ),
            'emergency_freeze_enabled': _parse_bool(
                os.getenv('EMERGENCY_FREEZE_ENABLED'),
                default=False
            ),
            'emergency_freeze_reason': os.getenv(
                'EMERGENCY_FREEZE_REASON',
                ''
            )
        }
    
    def get(self, key, default=None):
        """Get configuration value."""
        return self.config.get(key, default)
    
    def get_log_path(self, filename):
        """Get environment-specific log path."""
        log_dir = os.path.join("logs", f"{self.env}")
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, filename)