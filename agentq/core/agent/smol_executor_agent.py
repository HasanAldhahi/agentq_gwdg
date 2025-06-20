import os
import asyncio
from typing import Any, Dict
from smolagents import CodeAgent, OpenAIServerModel
from agentq.core.tools.browser_tools import (
    open_url,
    get_dom_content,
    click,
    enter_text,
    enter_text_and_click,
    get_current_url,
    get_screenshot,
    press_key,
    solve_captcha_tool,
    upload_file,
    wait_for_page_load,
)


# Create the model using smolagents' OpenAIServerModel
custom_model = OpenAIServerModel(
    model_id=os.environ.get("MODEL_NAME", "qwen3-32b"),
    api_base=os.environ.get("ACADEMIC_CLOUD_BASE_URL", "https://chat-ai.academiccloud.de/v1"),
    api_key=os.environ.get("ACADEMIC_CLOUD_API_KEY"),
    temperature=0.1,
    max_tokens=2000,
)

# This is now a comprehensive toolkit for browser automation.
browser_tool_list = [
    open_url,
    get_dom_content,
    click,
    enter_text,
    enter_text_and_click,
    get_current_url,
    get_screenshot,
    press_key,
    solve_captcha_tool,
    upload_file,
    wait_for_page_load,
]

# Create the agent that will execute code.
smol_executor = CodeAgent(
    tools=browser_tool_list,
    model=custom_model,
    additional_authorized_imports=["pandas", "numpy", "re", "json", "time"],
    stream_outputs=False,
)


async def execute_sub_task(sub_task: str) -> str:
    """
    Execute a sub-task using the smol_executor.
    
    Args:
        sub_task (str): Natural language description of the task to execute
        
    Returns:
        str: Result of the execution
    """
    try:
        # Run the executor in a thread to avoid blocking
        result = await asyncio.to_thread(smol_executor.run, sub_task)
        return str(result)
    except Exception as e:
        return f"Error executing sub-task '{sub_task}': {str(e)}" 