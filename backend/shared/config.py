import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")
    neo4j_uri: str = Field(..., env="NEO4J_URI")
    neo4j_user: str = Field(..., env="NEO4J_USER")
    neo4j_password: str = Field(..., env="NEO4J_PASSWORD")
    
    sportradar_api_key: Optional[str] = Field(None, env="SPORTRADAR_API_KEY")
    sportsdata_api_key: Optional[str] = Field(None, env="SPORTSDATA_API_KEY")
    draftkings_api_key: Optional[str] = Field(None, env="DRAFTKINGS_API_KEY")
    fanduel_api_key: Optional[str] = Field(None, env="FANDUEL_API_KEY")
    betmgm_api_key: Optional[str] = Field(None, env="BETMGM_API_KEY")
    news_api_key: Optional[str] = Field(None, env="NEWS_API_KEY")
    twitter_api_key: Optional[str] = Field(None, env="TWITTER_API_KEY")
    twitter_api_secret: Optional[str] = Field(None, env="TWITTER_API_SECRET")
    twitter_access_token: Optional[str] = Field(None, env="TWITTER_ACCESS_TOKEN")
    twitter_access_secret: Optional[str] = Field(None, env="TWITTER_ACCESS_SECRET")
    
    gemini_api_key: Optional[str] = Field(None, env="GEMINI_API_KEY")
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")

    # Podcast & Vector Database
    listen_notes_api_key: Optional[str] = Field(None, env="LISTEN_NOTES_API_KEY")
    assemblyai_api_key: Optional[str] = Field(None, env="ASSEMBLYAI_API_KEY")
    vector_db_path: str = Field("./chroma_db", env="VECTOR_DB_PATH")
    podcast_batch_size: int = Field(5, env="PODCAST_BATCH_SIZE")

    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(True, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")
    
    mlflow_tracking_uri: str = Field("http://localhost:5000", env="MLFLOW_TRACKING_URI")
    
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_secret: str = Field(..., env="JWT_SECRET")
    
    max_simulation_iterations: int = Field(100000, env="MAX_SIMULATION_ITERATIONS")
    optimization_timeout_minutes: int = Field(20, env="OPTIMIZATION_TIMEOUT_MINUTES")
    query_response_timeout_seconds: int = Field(5, env="QUERY_RESPONSE_TIMEOUT_SECONDS")
    
    salary_cap: int = Field(50000, env="SALARY_CAP")
    lineup_count: int = Field(150, env="LINEUP_COUNT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
