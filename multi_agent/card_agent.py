import logging
import boto3
import time
import json

from main_memory import main_memory

from strands import Agent, tool
from strands.models import BedrockModel
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

from strands.hooks import (HookProvider, 
                           HookRegistry, 
                           AfterInvocationEvent, 
                           AfterToolCallEvent, 
                           BeforeInvocationEvent, 
                           BeforeToolCallEvent
                    )

CARD_SYSTEM_PROMPT = """
    You are CARD agent specialized to handle all informations about CARD.

    Card Operations:
        1. get_card: Get CARD details such as card number, atc, type, model (CREDIT or DEBIT), status.
            - args: 
                - card: Exactly 12 digits split into 4 groups of 3 digits each.
            - response: 
                - card: details such as account associated, atc, card type, card model (CREDIT or DEBIT), card status.
        
        2. card_healthy: healthy CARD service status.
            - response: 
                - content: all information about CARD service health status and enviroment variables.
            Healthy Rule:
                - This tool must be triggered ONLY with a EXPLICITY requested.
                - return only the status code, consider 200 as healthy, otherwise unhealthy.

        3. create_card: Create a CARD, always assume that the account provided already exists.
            - args:
                - card: Exactly 12 digits split into 4 groups of 3 digits each.
                - account: account identificator (account_id) associated with a card. A account pattern is ACC-###.### or ACC-###
                - holder: card holder name.
                - type: CREDIT or DEBIT, the default value is CREDIT.
                - model: CHIP or VIRTUAL, the default value is CHIP.
                - status: ISSUED or PEDING, the default value is ISSUED.
            - response: 
                card: all card information. 

    Card Rules:
        1. All CARD numbers MUST be returned strictly in the format: 999.999.999.999
            - Exactly 12 digits split into 4 groups of 3 digits each.
            - Use '.' as the separator.
        2. If the input does not contain a valid card number, respond with: "INVALID FORMAT".
        3. Convert and format all dates using the format YYYY-MM-DD

    Definitions and rules:
        - Always use the mcp tools provided.
        - USE EXACTLY the fields names provided by json response. ex: account_id, person_id, card_number, etc.
        - DO NOT UPDATE any field format provided by mcp tool, use EXACTLY the mcp field result format.
"""

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup a model
#model_id = lite pro premier
model_id = "arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-pro-v1:0"  

logger.info('\033[1;33m Starting the Card Agent... \033[0m')
logger.info(f'\033[1;33m model_id: {model_id} \033[0m \n')

# Create boto3 session
session = boto3.Session(
    region_name='us-east-2',
)

bedrock_model = BedrockModel(
        model_id=model_id,
        temperature=0.0,
        boto_session=session,
)

# load mcp servers
mcp_url = "http://127.0.0.1:9002/mcp"

def create_streamable_http_mcp_server(mcp_url: str):
    return streamablehttp_client(mcp_url)

streamable_http_mcp_server = MCPClient(lambda: create_streamable_http_mcp_server(mcp_url))

class ToolValidationError(Exception):
    """Custom exception to abort tool calls immediately."""
    pass

# Agent hook setup
class AgentHook(HookProvider):

    def __init__(self):
        self.start_agent = ""
        self.tool_name = "unknown"
        self.metrics = {}

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.agent_start)
        registry.add_callback(AfterInvocationEvent, self.agent_end)
        registry.add_callback(BeforeToolCallEvent, self.before_tool)
        registry.add_callback(AfterToolCallEvent, self.after_tool)

    def agent_start(self, event: BeforeInvocationEvent) -> None:
        logger.info(f" *** BeforeInvocationEvent **** ")
        self.start_agent = time.time()
        logger.info(f"Request started - Agent: {event.agent.name} : { self.start_agent }")

    def agent_end(self, event: AfterInvocationEvent) -> None:
        logger.info(f" *** AfterInvocationEvent **** ")

        duration = time.time() - self.start_agent
        logger.info(f"Request completed - Agent: {event.agent.name} - Duration: {duration:.2f}s")
        
        self.metrics["total_requests"] = self.metrics.get("total_requests", 0) + 1
        self.metrics["avg_duration"] = (
            self.metrics.get("avg_duration", 0) * 0.9 + duration * 0.1 # Exponencial Moving Average 
        )

        logger.info(f" *** *** self.metrics *** *** ")
        logger.info(f" {self.metrics}")
        logger.info(f" *** *** self.metrics *** *** ")

    def before_tool(self, event: BeforeToolCallEvent) -> None:
        logger.info(f"*** Tool invocation - agent: {event.agent.name} : { event.tool_use.get('name') } *** ")

    def after_tool(self, event: AfterToolCallEvent) -> None:
        logger.info(f" *** AfterToolCallEvent **** ")
        
        self.tool_name = event.tool_use.get("name")
        logger.info(f"* Tool completed - agent: {event.agent.name} : {self.tool_name}")

@tool
def card_agent(query: str) -> str:
    """
    Process and respond all CARD queries using a specialized CARD agent.
    
    Args:
        query: Given a card, create a card, get card information and details, and check healthy status.
        
    Returns:
        a card with its details.
    """
    logger.info("function => card_agent()")

    token = main_memory.get_token()
    if not token:
        logger.error("Error, I couldn't process No JWT token available")
        return "Error, but I couldn't process No JWT token available"
         
    context={"jwt":token}

    # Format the query for the agent
    formatted_query = f"Please process the following query: {query} with context:{context}"
    all_tools = []
    
    try:
        logger.info("Routed to Card Agent")

        agent_hook = AgentHook()

        with streamable_http_mcp_server:
            all_tools.extend(streamable_http_mcp_server.list_tools_sync())

            selected_tools = [
                t for t in all_tools 
                if t.tool_name in ["card_healthy", 
                                   "create_card",
                                   "get_card"]
            ]

            logger.info(f"Available MCP tools: {[tool.tool_name for tool in selected_tools]}")

            # Create the math agent with calculator capability
            agent = Agent(name="main",
                        system_prompt=CARD_SYSTEM_PROMPT,
                        model=bedrock_model, 
                        tools=selected_tools,
                        hooks=[agent_hook],
                        callback_handler=None
                    )
            
            try:
                agent_response = agent(formatted_query)
                text_response = str(agent_response)

                if len(text_response) > 0:
                    return json.dumps({
                        "status": "success",
                        "response": text_response
                    })

                return json.dumps({
                    "status": "error",
                    "reason": "Error but I couldn't process this request due a problem. Please check if your query is clearly stated or try rephrasing it."
                })
                          
            except ToolValidationError as e:
                logger.error(f"Transaction aborted: {e}")
                return json.dumps({
                    "status": "error",
                    "reason": f"Transaction aborted: {str(e)}"
                })
            
    except Exception as e:
        logger.error(f"Error processing your query: {str(e)}")
        return json.dumps({
            "status": "error",
            "reason": f"Error processing your query: {str(e)}"
        })