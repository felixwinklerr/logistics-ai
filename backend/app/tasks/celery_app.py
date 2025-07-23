"""
Celery application configuration for background task processing
"""

from celery import Celery
from app.core.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "logistics_ai",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.email_tasks",
        "app.tasks.ai_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "app.tasks.email_tasks.*": {"queue": "email"},
        "app.tasks.ai_tasks.*": {"queue": "ai"},
    },
    
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Bucharest",
    enable_utc=True,
    
    # Task execution settings
    task_always_eager=False,  # Set to True for testing
    task_eager_propagates=True,
    task_ignore_result=False,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=100,
    
    # Task retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={"master_name": "mymaster"},
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "email-monitoring-health-check": {
            "task": "app.tasks.email_tasks.health_check_email_monitoring",
            "schedule": 300.0,  # Every 5 minutes
        },
        "cleanup-old-email-records": {
            "task": "app.tasks.email_tasks.cleanup_old_email_records",
            "schedule": 3600.0,  # Every hour
        },
    },
    beat_scheduler="celery.beat:PersistentScheduler",
)

# Optional: Custom task base class
class CallbackTask(celery_app.Task):
    """Base class for tasks with callback support"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Success callback"""
        pass
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Failure callback"""
        pass

# Auto-discover tasks
celery_app.autodiscover_tasks() 