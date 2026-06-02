import multiprocessing

class Settings:
    PROJECT_NAME: str = "Micc API"
    API_V1_STR: str = "/api/v1"
    MAX_WORKERS: int = max(1, multiprocessing.cpu_count() - 1)

settings = Settings()
