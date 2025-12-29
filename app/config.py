import os
import json
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class HiveConfig(BaseModel):
    host: str = "localhost"
    port: int = 10000
    username: Optional[str] = None
    password: Optional[str] = None
    database: str = "default"
    auth: Optional[str] = "NOSASL"
    configuration: Dict[str, Any] = {}

class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8008
    max_rows: int = 1000

class Config(BaseModel):
    hive: HiveConfig
    allowed_origins: Optional[List[str]] = None
    server: ServerConfig = ServerConfig()

    @classmethod
    def load(cls, config_path: str = "config.json") -> "Config":
        if not os.path.exists(config_path):
             # Fallback to creating a default config if not found, or raising error
             # For now, let's assume it might not exist and return defaults, 
             # but in this project config.json is expected.
             # Let's try to look in the parent directory if not found (common in dev).
             parent_config = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
             if os.path.exists(parent_config):
                 config_path = parent_config
             else:
                 return cls(hive=HiveConfig()) # Return default

        with open(config_path, "r") as f:
            data = json.load(f)
        
        # Handle env var overrides
        hive_data = data.get("hive", {})
        hive_data["host"] = os.getenv("HIVE_HOST", hive_data.get("host", "localhost"))
        hive_data["port"] = int(os.getenv("HIVE_PORT", hive_data.get("port", 10000)))
        hive_data["username"] = os.getenv("HIVE_USERNAME", hive_data.get("username"))
        hive_data["password"] = os.getenv("HIVE_PASSWORD", hive_data.get("password"))
        hive_data["auth"] = os.getenv("HIVE_AUTH", hive_data.get("auth", "NOSASL"))
        
        data["hive"] = hive_data
        return cls(**data)

    def mask_secrets(self) -> Dict[str, Any]:
        """Return a dict representation with secrets masked for logging."""
        d = self.model_dump()
        if d.get("hive", {}).get("password"):
            d["hive"]["password"] = "***"
        return d

# Global config instance
config = Config.load()
