import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    banking_service_url: str = os.getenv("BANKING_SERVICE_URL", "http://localhost:8001")
    llm_provider: str = os.getenv("LLM_PROVIDER", "demo").lower()
    aws_region: str = os.getenv("AWS_REGION", "eu-central-1")
    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0"
    )
    policy_path: Path = Path(
        os.getenv(
            "POLICY_PATH",
            str(Path(__file__).resolve().parents[2] / "policies" / "reconciliation_policy.md"),
        )
    )


settings = Settings()
