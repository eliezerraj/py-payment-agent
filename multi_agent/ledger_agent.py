import logging
import boto3

from main_memory import main_memory

from strands import Agent, tool
from strands.models import BedrockModel
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

LEDGER_SYSTEM_PROMPT = """
    You are LEDGER agent specialized to handle informations about LEDGER.

    Ledger Operations :
        1. get_account_statement: get account activity, account balances and statements from a given account (account id).
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
def create_streamable_http_mcp_server():
    return streamablehttp_client("http://localhost:9002/mcp")

streamable_http_mcp_server = MCPClient(create_streamable_http_mcp_server)

@tool
def ledger_agent(query: str) -> str:
    """
    Process and respond all LEDGER queries using a specialized LEDGER agent.

    Args:
        query: Given an account identificator (account_id) get information such as ledger service healhy status, bank statement, financial moviment, account activity, balances.
        
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

            selected_tools = [
                t for t in all_tools 
                if t.tool_name in ["ledger_healthy", "get_account_statement"]
            ]

            logger.info(f"Available MCP tools: {[tool.tool_name for tool in selected_tools]}")

            # Create the math agent with calculator capability
            agent = Agent(name="main",
                        system_prompt=LEDGER_SYSTEM_PROMPT,
                        model=bedrock_model, 
                        tools=selected_tools,
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