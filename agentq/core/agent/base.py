import json
import os
from typing import Callable, List, Optional, Tuple, Type

import instructor
import instructor.patch
import litellm
import openai
from instructor import Mode
from langsmith import traceable
from pydantic import BaseModel

from agentq.config.config import API_KEY, BASE_URL, MODEL
from agentq.utils.function_utils import get_function_schema
from agentq.utils.logger import logger


class BaseAgent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        input_format: Type[BaseModel],
        output_format: Type[BaseModel],
        tools: Optional[List[Tuple[Callable, str]]] = None,
        keep_message_history: bool = True,
        client: str = "academic_cloud",
    ):
        # Metdata
        self.agent_name = name

        # Messages
        self.system_prompt = system_prompt
        # handling the case where agent has to do async intialisation as system prompt depends on some async functions.
        # in those cases, we do init with empty system prompt string and then handle adding system prompt to messages array in the agent itself
        if self.system_prompt:
            self._initialize_messages()
        self.keep_message_history = keep_message_history

        # Input-output format
        self.input_format = input_format
        self.output_format = output_format

        # Set global configurations for litellm
        litellm.logging = False
        litellm.set_verbose = False

        # LLM client initialization
        if client == "academic_cloud":
            print("--- Initializing Academic Cloud Client ---")
            api_key = os.environ.get("ACADEMIC_CLOUD_API_KEY")
            base_url = os.environ.get("ACADEMIC_CLOUD_BASE_URL")
            print(f"Base URL: {base_url}")
            print(f"API Key found: {'Yes' if api_key else 'No'}")

            if not api_key or not base_url:
                raise ValueError("ACADEMIC_CLOUD_API_KEY and ACADEMIC_CLOUD_BASE_URL must be set in your .env file")

            self.client = openai.OpenAI(
                base_url=base_url,
                api_key=api_key,
            )
        elif client == "openai":
            self.client = openai.OpenAI()
        elif client == "together":
            self.client = openai.OpenAI(
                base_url="https://api.together.xyz/v1",
                api_key=os.environ["TOGETHER_API_KEY"],
            )

        # Tools
        self.tools_list = []
        self.executable_functions_list = {}
        if tools:
            self._initialize_tools(tools)

    def _initialize_tools(self, tools: List[Tuple[Callable, str]]):
        for func, func_desc in tools:
            self.tools_list.append(get_function_schema(func, description=func_desc))
            self.executable_functions_list[func.__name__] = func

    def _initialize_messages(self):
        self.messages = [{"role": "system", "content": self.system_prompt}]

    @traceable(run_type="chain", name="agent_run")
    async def run(
        self,
        input_data: BaseModel,
        screenshot: str = None,
        session_id: str = None,
    ) -> BaseModel:


        # # --- START DIAGNOSTIC CODE ---
        # try:
        #     print("\n--- RUNNING DIAGNOSTIC: PLAIN OPENAI CALL ---")
        #     plain_client = openai.OpenAI(
        #         base_url=os.environ.get("ACADEMIC_CLOUD_BASE_URL"),
        #         api_key=os.environ.get("ACADEMIC_CLOUD_API_KEY"),
        #     )
        #     # Use a simple message list for the test
        #     test_messages = [{"role": "user", "content": "Hello!"}]
        #     test_response = plain_client.chat.completions.create(
        #         model=model_name,
        #         messages=test_messages,
        #         response_format={"type": "json_object"},
        #         # temperature=0.0,
        #         # timeout=30,
        #     )
        #     print("--- DIAGNOSTIC SUCCEEDED ---")
        #     print("Response:", test_response.choices[0].message.content)

        # except Exception as e:
        #     print(f"--- DIAGNOSTIC FAILED ---")
        #     print(f"Error: {e}\n")
        # # --- END DIAGNOSTIC CODE ---

        if not isinstance(input_data, self.input_format):
            raise ValueError(f"Input data must be of type {self.input_format.__name__}")

        # Handle message history.
        if not self.keep_message_history:
            self._initialize_messages()

        # HYBRID APPROACH: If screenshot provided, use vision model for analysis first
        visual_analysis = None
        if screenshot:
            print("🔍 Analyzing screenshot with vision model...")
            visual_analysis = await self._analyze_screenshot_with_vision(screenshot, input_data)
            print(f"📸 Visual analysis: {visual_analysis}")

        # Use text model for decision making (with visual context if available)
        model_name = os.environ.get("MODEL_NAME", "qwen3-32b")
        print(f"--- Using Text Model for API call ---")
        print(f"Model Name: {model_name}")

        # Prepare messages for the text model
        if visual_analysis:
            # Enhanced input with visual context
            enhanced_content = f"""
VISUAL ANALYSIS: {visual_analysis}

USER INPUT: {input_data.model_dump_json(exclude={"current_page_dom", "current_page_url"})}
"""
            self.messages.append({
                "role": "user",
                "content": enhanced_content
            })
        else:
            # Regular input without visual analysis
            self.messages.append({
                "role": "user",
                "content": input_data.model_dump_json(
                    exclude={"current_page_dom", "current_page_url"}
                ),
            })

        # Add DOM and URL in a separate message (original approach)
        if hasattr(input_data, "current_page_dom") and hasattr(input_data, "current_page_url"):
            self.messages.append({
                "role": "user",
                "content": f"Current page URL:\n{input_data.current_page_url}\n\n Current page DOM:\n{input_data.current_page_dom}",
            })

        # Add JSON format instruction to system prompt
        json_instruction = f"\n\nYou must respond with valid JSON that matches this exact schema: {self.output_format.model_json_schema()}\n\nImportant: Optional fields (marked with 'anyOf' containing 'null') can either be omitted from your response or set to null. Required fields must always be included."
        self.messages[0]["content"] += json_instruction

        # logger.info(self.messages)

        # TODO: add a max_turn here to prevent a inifinite fallout
        while True:
            # TODO:
            # 1. exeception handling while calling the client
            # 2. remove the else block as JSON mode in instrutor won't allow us to pass in tools.
            logger.info(f"[{self.agent_name}] Preparing to call LLM with model: {model_name}")
            if len(self.tools_list) == 0:
                logger.info(f"[{self.agent_name}] Calling LLM without tools.")
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=self.messages,
                    response_format={"type": "json_object"},
                    # max_retries=4,
                    # timeout=60,
                )
                logger.info(f"[{self.agent_name}] LLM call successful.")
            else:
                logger.info(f"[{self.agent_name}] Calling LLM with tools.")
                # For now, disable tools since they require special support
                # response = self.client.chat.completions.create(
                #     model=model_name,
                #     messages=self.messages,
                #     response_format={"type": "json_object"},
                #     tool_choice="auto",
                #     tools=self.tools_list,
                # )
                # Use the same call as the no-tools case for now
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=self.messages,
                    response_format={"type": "json_object"},
                    # max_retries=4,
                    # timeout=60,
                )
                logger.info(f"[{self.agent_name}] LLM call successful.")

            # Parse the JSON response manually
            response_content = response.choices[0].message.content
            logger.info(f"[{self.agent_name}] Raw response: {response_content}")
            
            try:
                # Parse the JSON response
                json_response = json.loads(response_content)
                logger.info(f"[{self.agent_name}] Parsed JSON keys: {list(json_response.keys())}")
                
                # Handle missing optional fields by adding defaults
                # Get the model's field definitions
                model_fields = self.output_format.model_fields
                logger.info(f"[{self.agent_name}] Expected fields: {list(model_fields.keys())}")
                
                for field_name, field_info in model_fields.items():
                    # If field is missing and is truly optional (has Union with NoneType), add None as default
                    if field_name not in json_response:
                        # Check if the field annotation includes NoneType (meaning it's Optional)
                        field_annotation = field_info.annotation
                        if hasattr(field_annotation, '__args__') and type(None) in field_annotation.__args__:
                            logger.info(f"[{self.agent_name}] Adding None for optional field: {field_name}")
                            json_response[field_name] = None
                        else:
                            logger.error(f"[{self.agent_name}] Missing required field: {field_name}")
                
                # Convert to the expected Pydantic model
                parsed_response = self.output_format(**json_response)
                logger.info(f"[{self.agent_name}] Successfully parsed response")
                return parsed_response
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"[{self.agent_name}] Failed to parse response: {e}")
                logger.error(f"[{self.agent_name}] Raw response was: {response_content}")
                # You might want to retry here or raise the error
                raise ValueError(f"Failed to parse LLM response as valid JSON: {e}")

    async def _analyze_screenshot_with_vision(self, screenshot: str, input_data) -> str:
        """
        Use internvl2.5-8b vision model to analyze screenshot and provide visual context
        """
        try:
            vision_model = "internvl2.5-8b"
            print(f"Using vision model: {vision_model}")
            
            vision_prompt = f"""
            You are a web automation visual analyst. Analyze this screenshot and provide a brief description of:
            1. What type of webpage this is
            2. Any visible popups, modals, or overlays (especially cookie banners, privacy notices)
            3. Key interactive elements visible (buttons, forms, search boxes, links)
            4. Any obstacles that might block interaction with the main content
            5. Overall layout and what the user can see
            
            User's objective: {input_data.objective}
            
            Be specific about visual elements that might need to be addressed before the main task.
            Respond in JSON format like: {{"visual_analysis": "your detailed analysis here"}}
            """
            
            messages = [
                {"role": "system", "content": "You are a visual analyst for web automation. Provide clear, actionable visual insights in JSON format."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": vision_prompt},
                        {"type": "image_url", "image_url": {"url": screenshot}},
                    ]
                }
            ]
            
            response = self.client.chat.completions.create(
                model=vision_model,
                messages=messages,
                response_format={"type": "json_object"},
            )
            
            raw_response = response.choices[0].message.content
            parsed = json.loads(raw_response)
            return parsed.get("visual_analysis", "No visual analysis available")
            
        except Exception as e:
            logger.warning(f"Vision analysis failed: {e}")
            return "Vision analysis unavailable - proceeding with DOM-only analysis"

    async def _append_tool_response(self, tool_call):
        function_name = tool_call.function.name
        function_to_call = self.executable_functions_list[function_name]
        function_args = json.loads(tool_call.function.arguments)
        try:
            function_response = await function_to_call(**function_args)
            # print(function_response)
            self.messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(function_response),
                }
            )
        except Exception as e:
            logger.error(f"Error occurred calling the tool {function_name}: {str(e)}")
            self.messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": str(
                        "The tool responded with an error, please try again with a different tool or modify the parameters of the tool",
                        function_response,
                    ),
                }
            )
