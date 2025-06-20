import os
from pydantic import BaseModel
from typing_extensions import Annotated

from agentq.core.agent.base import BaseAgent
from agentq.core.models.models import VisionInput, VisionOutput
from agentq.core.prompts.prompts import LLM_PROMPTS


class VisionAgent(BaseAgent):
    def __init__(self, client: str = "academic_cloud"):
        system_prompt: str = LLM_PROMPTS["VISION_AGENT_PROMPT"]
        self.name = "vision"

        super().__init__(
            name=self.name,
            system_prompt=system_prompt,
            input_format=VisionInput,
            output_format=VisionOutput,
            keep_message_history=False,
            client=client,
        )

    async def run(
        self,
        input_data: BaseModel,
        screenshot: str = None,
        session_id: str = None,
    ) -> BaseModel:
        """
        Runs the vision model with the specific model name from environment variables.
        """
        vision_model_name = os.environ.get("VISION_MODEL_NAME", "internvl2.5-8b")
        
        return await super().run(
            input_data=input_data,
            screenshot=screenshot,
            session_id=session_id,
            model=vision_model_name
        )
