from typing import Dict, Any, Optional, Union, List
from typing_extensions import Annotated

from smolagents import tool
from agentq.core.web_driver.playwright import PlaywrightManager
from agentq.utils.logger import logger
from agentq.utils.get_detailed_accessibility_tree import do_get_accessibility_info
from agentq.core.skills.enter_text_using_selector import EnterTextEntry, entertext
from agentq.core.skills.click_using_selector import click
from agentq.core.skills.open_url import openurl
from agentq.core.skills.get_url import geturl
from agentq.core.skills.enter_text_and_click import enter_text_and_click as enter_text_and_click_skill
from agentq.core.skills.get_screenshot import get_screenshot as get_screenshot_skill
from agentq.core.skills.solve_captcha import solve_captcha as solve_captcha_skill
from agentq.core.skills.upload_file import upload_file as upload_file_skill
from agentq.core.skills.press_key_combination import press_key_combination as press_key_combination_skill

# Note: We import the internal logic functions to avoid circular dependencies


@tool
async def open_url(
    url: Annotated[str, "The full URL to navigate to, including the protocol (http:// or https://)."],
    timeout: Annotated[int, "Optional wait time in seconds after the page loads."] = 5
) -> Annotated[str, "A confirmation message with the title of the new page."]:
    """
    Opens a specified URL in the browser and waits for it to load.
    
    Args:
        url (str): The URL to navigate to.
        timeout (int): Additional time to wait after the page has loaded.
    """
    try:
        await openurl(url=url, timeout=timeout)
        browser_manager = PlaywrightManager()
        page = await browser_manager.get_current_page()
        title = await page.title()
        return f"Successfully navigated to page: {title}"
    except Exception as e:
        return f"Error navigating to URL: {str(e)}"


@tool
async def get_dom_content(
    content_type: Annotated[
        str,
        "Specify 'all_fields' for a detailed DOM tree, 'input_fields' for form elements, or 'text_only' for page text.",
    ] = "all_fields"
) -> Annotated[Union[Dict[str, Any], str, None], "A JSON object of the DOM or a string of the page's text content."]:
    """
    Retrieves the Document Object Model (DOM) of the current page.

    Args:
        content_type (str): Can be 'all_fields', 'input_fields', or 'text_only'.
    """
    try:
        browser_manager = PlaywrightManager()
        page = await browser_manager.get_current_page()
        
        if content_type == "input_fields":
            dom_content = await do_get_accessibility_info(page, only_input_fields=True)
        else:
            dom_content = await do_get_accessibility_info(page, only_input_fields=False)
            
        return dom_content
    except Exception as e:
        return f"Error getting DOM content: {str(e)}"


@tool
async def click(
    selector: Annotated[
        str,
        "The CSS selector of the element to click (e.g., '[mmid=\"123\"]'). Use the 'mmid' attribute from the DOM content.",
    ]
) -> Annotated[str, "A message indicating the success or failure of the click action."]:
    """
    Performs a click action on a specific element identified by its CSS selector.

    Args:
        selector (str): The CSS selector to identify the element to be clicked.
    """
    try:
        result = await click(selector=selector, wait_before_execution=1.0)
        return f"Successfully clicked element with selector: {selector}"
    except Exception as e:
        return f"Error clicking element: {str(e)}"


@tool
async def enter_text(
    selector: Annotated[str, "The CSS selector for the input field, using the 'mmid' attribute."],
    text_to_enter: Annotated[str, "The text to type into the input field."],
) -> Annotated[str, "A confirmation message."]:
    """
    Enters text into a specified input field on the page.

    Args:
        selector (str): The CSS selector of the input field.
        text_to_enter (str): The text to be entered.
    """
    try:
        entry = EnterTextEntry(
            query_selector=selector,
            text=text_to_enter,
        )
        await entertext(entry)
        return f"Successfully entered text '{text_to_enter}' into element: {selector}"
    except Exception as e:
        return f"Error entering text: {str(e)}"


@tool
async def enter_text_and_click(
    text_selector: Annotated[str, "The CSS selector for the text input field."],
    text_to_enter: Annotated[str, "The text to enter."],
    click_selector: Annotated[str, "The CSS selector for the element to click after text entry."],
) -> Annotated[str, "A confirmation of the combined action."]:
    """
    Enters text into an element and then clicks on another element in a single step.

    Args:
        text_selector (str): The CSS selector for the text field.
        text_to_enter (str): The text to enter.
        click_selector (str): The CSS selector for the element to click.
    """
    try:
        result = await enter_text_and_click_skill(
            text_selector=text_selector,
            text_to_enter=text_to_enter,
            click_selector=click_selector,
            wait_before_click_execution=1.5
        )
        return f"Successfully entered text '{text_to_enter}' and clicked element"
    except Exception as e:
        return f"Error in enter_text_and_click: {str(e)}"


@tool
async def get_current_url() -> Annotated[str, "The current URL of the browser tab."]:
    """Returns the URL of the current page."""
    try:
        url = await geturl()
        return url
    except Exception as e:
        return f"Error getting current URL: {str(e)}"


@tool
async def get_screenshot() -> Annotated[str, "A base64 encoded string of the screenshot."]:
    """Captures a screenshot of the current viewport and returns it as a base64 encoded string."""
    try:
        screenshot_b64 = await get_screenshot_skill()
        return f"Screenshot captured successfully (length: {len(screenshot_b64)} characters)"
    except Exception as e:
        return f"Error capturing screenshot: {str(e)}"


@tool
async def press_key(
    key_combination: Annotated[str, "The key or key combination to press (e.g., 'Enter', 'Control+C')."]
) -> Annotated[str, "A confirmation message."]:
    """
    Presses a key or a combination of keys on the current page.

    Args:
        key_combination (str): The key to press, e.g., 'Enter', 'PageDown', 'Control+A'.
    """
    try:
        result = await press_key_combination_skill(key_combination)
        return f"Successfully pressed key combination: {key_combination}"
    except Exception as e:
        return f"Error pressing key: {str(e)}"


@tool
async def solve_captcha_tool(
    text_selector: Annotated[str, "The CSS selector where the captcha solution should be entered."],
    click_selector: Annotated[str, "The CSS selector of the submit button to click after entering the solution."],
) -> Annotated[str, "A message indicating the result of the captcha solving attempt."]:
    """
    Uses a vision model to solve a captcha, enters the solution, and clicks the submit button.

    Args:
        text_selector (str): The selector for the captcha input field.
        click_selector (str): The selector for the submit button.
    """
    try:
        result = await solve_captcha_skill(
            text_selector=text_selector,
            click_selector=click_selector,
            wait_before_click_execution=1.0
        )
        return f"Captcha solving attempted. Result: {result}"
    except Exception as e:
        return f"Error solving captcha: {str(e)}"


@tool
async def upload_file(
    selector: Annotated[str, "The CSS selector for the file input element."],
    file_path: Annotated[str, "The local path to the file to be uploaded."],
) -> Annotated[str, "A message indicating if the file upload was successful."]:
    """
    Uploads a local file to the webpage.

    Args:
        selector (str): The CSS selector of the file input element.
        file_path (str): The path to the local file.
    """
    try:
        result = await upload_file_skill(selector=selector, file_path=file_path)
        return f"File upload attempted for: {file_path}"
    except Exception as e:
        return f"Error uploading file: {str(e)}"


@tool
async def wait_for_page_load(
    timeout: Annotated[int, "Maximum time to wait in seconds."] = 10
) -> Annotated[str, "Confirmation that page has loaded."]:
    """
    Waits for the page to finish loading.
    
    Args:
        timeout (int): Maximum time to wait for page load.
    """
    try:
        browser_manager = PlaywrightManager()
        page = await browser_manager.get_current_page()
        await page.wait_for_load_state("networkidle", timeout=timeout * 1000)
        return "Page has finished loading"
    except Exception as e:
        return f"Error waiting for page load: {str(e)}" 