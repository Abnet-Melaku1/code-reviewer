from arq.connections import RedisSettings

from codereviewer.worker.config import WorkerConfig
from codereviewer.worker.jobs import index_repo, review_pr

config = WorkerConfig()


class WorkerSettings:
    """arq settings to load and run background worker instances."""

    functions = [index_repo, review_pr]
    redis_settings = RedisSettings.from_dsn(config.redis_url)
