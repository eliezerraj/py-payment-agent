import logging
import boto3

from main_memory import main_memory

from strands import Agent, tool
from strands.models import BedrockModel
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

LEDGER_SYSTEM_PROMPT = """
    You are LEDGER agent specialized to handle all LEDGER informations such as bank statement, financial moviment, account activity and account balances.

    Ledger Activity :
        1. get_account_statement: Get account activity, account balances and statements from a given account
            - args: account id
            - response: A list of bank statement, financial moviment, account activity and account balance summary 
        2. ledger_healthy: healthy ledger service status
            - response: only the status code from api, consider 200 as healthy, otherwise unhealthy

    Definitions:
        Always use the mcp tools provided
"""

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Starting the Ledger Agent...")

# Create boto3 session
session = boto3.Session(
    region_name='us-east-2',
)

# Setup a model
model_id = "arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-premier-v1:0"  

bedrock_model = BedrockModel(
        model_id=model_id,
        temperature=0.0,
        boto_session=session,
)

# load mcp servers
def create_streamable_http_mcp_server():
    return streamablehttp_client("http://localhost:9002/mcp")

streamable_http_mcp_server = MCPClient(create_streamable_http_mcp_server)

@tool
def ledger_agent(query: str) -> str:
    """
    Process and respond all ledger queries using a specialized ledger agent such as:

    Args:
        query: Given an account id get informations such as healhy status, bank statement, financial moviment, account activity, balances.
        
    Returns:
        ledger information such as bank statement, financial moviment, account activity, balances.
    """
    logger.info("function => ledger_agent")

    token = main_memory.get_token()
    if not token:
        logger.error("Error, I couldn't process No JWT token available")
        return "Error, I couldn't process No JWT token available"
         
    context={"jwt":token}

    # Format the query for the agent
    formatted_query = f"Please process the following query: {query} with context:{context}"
    all_tools = []
 
    try:
        logger.info("Routed to Ledger Agent")
        
        with streamable_http_mcp_server:
            all_tools.extend(streamable_http_mcp_server.list_tools_sync())

            logger.info(f"Available MCP tools: {[tool.tool_name for tool in all_tools]}")

            # Create the math agent with calculator capability
            agent = Agent(name="main",
                        system_prompt=LEDGER_SYSTEM_PROMPT,
                        model=bedrock_model, 
                        tools=all_tools,
                        callback_handler=None
                    )
            
            agent_response = agent(formatted_query)
            text_response = str(agent_response)

            if len(text_response) > 0:
                return text_response

            return "Error but I couldn't process this request due a problem. Please check if your query is clearly stated or try rephrasing it."
    
    except Exception as e:
        # Return specific error message for math processing
        return f"Error processing your query: {str(e)}"