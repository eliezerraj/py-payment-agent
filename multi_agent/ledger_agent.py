import logging
import boto3
import time
import json

from main_memory import main_memory

from mcp.client.streamable_http import streamablehttp_client

from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient

from strands.hooks import (HookProvider, 
                           HookRegistry, 
                           AfterInvocationEvent, 
                           AfterToolCallEvent, 
                           BeforeInvocationEvent, 
                           BeforeToolCallEvent
                    )

LEDGER_SYSTEM_PROMPT = """
    You are LEDGER agent specialized to handle informations about LEDGER.

    Ledger Operations :
        1. get_account_statement: get all transaction activity, account balance, statements from a given account (account id).
            - args: 
                - account: account identificator (account_id).
            - response: 
                - list: A list of bank statement, financial moviment, account activity and balance summary.
        
        2. ledger_healthy: check the healthy status LEDGER service.
            - response:
                - content: all information about LEDGER service health status and enviroment variables. 
            Healthy Rule::
                - This tool must be triggered ONLY with a EXPLICITY requested.
                - return only the status code, consider 200 as healthy, otherwise unhealthy.

        3. create_moviment_transaction: Create a transaction over an account, always assume that the account provided already exists.
            - args:
                - account: account identificator (account_id) associated with a card. A account pattern is ACC-###.### or ACC-###.
                - type: DEPOSIT or WITHDRAW, the default value is DEPOSIT.
                - currency: transaction currency as BRL, the default value is BRL.
                - amount: transaction amount (float).
            - response:
                - transaction: all transaction information.

    Definitions and rules:
        - Always use the mcp tools provided.
        - USE EXACTLY the fields names provided by json response. ex: account_id, person_id, etc.
        - DO NOT UPDATE any field format provided by mcp tool, use EXACTLY the mcp field result format.
"""

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup a model
#model_id = lite pro premier
model_id = "arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-premier-v1:0"  

logger.info('\033[1;33m Starting the Ledger Agent... \033[0m')
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

        self.tool_name = event.tool_use.get("name")
        tool_input = event.tool_use.get("input", {})

        if self.tool_name == "create_moviment_transaction":
            amount = tool_input.get("amount")
    
            try:
                amount = float(amount)
            except Exception:
                logger.error(f"Invalid amount: {amount}. Must be a numeric.")
                event.abort = True
                raise ToolValidationError(f"Invalid amount: {amount}. Must be a numeric.")
            
            # Apply constraints
            if amount <= 0 or amount > 1000:
                logger.error(f"Invalid amount {amount}. Must be greater than 0 and less than 1000.")
                event.abort = True
                raise ToolValidationError(f"Invalid amount {amount}.  Must be greater than 0 and less than 1000")
        
            logger.info(f"[LedgerHook] Validated transaction amount: {amount}")

    def after_tool(self, event: AfterToolCallEvent) -> None:
        logger.info(f" *** AfterToolCallEvent **** ")
        
        self.tool_name = event.tool_use.get("name")
        logger.info(f"* Tool completed - agent: {event.agent.name} : {self.tool_name}")

@tool
def ledger_agent(query: str) -> str:
    """
    Process and respond all LEDGER queries using a specialized LEDGER agent.

    Args:
        query: Given an transaction, create a transaction, get information such as ledger service healhy status, bank statement, financial moviment, account activity, balances.
        
    Returns:
        ledger information such as bank statement, financial moviment, account activity, balances.
    """

    logger.info("function => ledger_agent")

    # load access token
    token = main_memory.get_token()
    if not token:
        logger.error("Error, I couldn't process No JWT token available")
        return "Error, I couldn't process No JWT token available"
         
    context={"jwt":token}

    try:
        logger.info("Routed to Ledger Agent")
        
        agent_hook = AgentHook()

        # Format the query for the agent
        formatted_query = f"Please process the following query: {query} with context: {context} and extract structured information"
        all_tools = []
        
        with streamable_http_mcp_server:
            all_tools.extend(streamable_http_mcp_server.list_tools_sync())

            selected_tools = [
                t for t in all_tools 
                if t.tool_name in ["ledger_healthy",
                                   "create_moviment_transaction", 
                                   "get_account_statement"]
            ]

            logger.info(f"Available MCP tools: {[tool.tool_name for tool in selected_tools]}")

            # Create the math agent with calculator capability
            agent = Agent(name="main",
                        system_prompt=LEDGER_SYSTEM_PROMPT,
                        model=bedrock_model, 
                        tools=selected_tools,
                        hooks=[agent_hook],
                        callback_handler=None,
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