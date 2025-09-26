import logging
import boto3

from strands import Agent, tool
from strands.models import BedrockModel
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

ACCOUNT_SYSTEM_PROMPT = """
    You are account agent specialized to handle all informations about ACCOUNT such as:

    Account Operations:
        1. get_account: Get account details from a endpoint via rest call api
            - args: Account Id
            - response: Account details like, assount id, owner account (person), dates of creation
        2. get_accounts_from_person: Given a person get all accounts associated
            - args: Person Id
            - reponse: List of accounts owned by a given person
        3. account_healthy: healthy account service status
            - response: only the status code from api, consider 200 as healthy, otherwise unhealthy

    Definitions:
        Always use the mcp tools provided
"""

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
def account_agent(query: str) -> str:
    """
    Process and respond all account queries using a specialized account agent.
    
    Args:
        query: Given an account get information and details such as healthy status, account´s person (owner), creation date, etc
        
    Returns:
        an account with its details
    """
    logger.info("function => account_agent")

    # Format the query for the agent
    formatted_query = f"Please process the following query: {query}"
    
    all_tools = []

    try:
        logger.info("Routed to Account Agent")
        
        with streamable_http_mcp_server:
            all_tools.extend(streamable_http_mcp_server.list_tools_sync())

            logger.info(f"Available MCP tools: {[tool.tool_name for tool in all_tools]}")

            # Create the math agent with calculator capability
            agent = Agent(name="main",
                        system_prompt=ACCOUNT_SYSTEM_PROMPT,
                        model=bedrock_model, 
                        tools=all_tools,
                        callback_handler=None
                    )
            
            agent_response = agent(formatted_query)
            text_response = str(agent_response)

            if len(text_response) > 0:
                return text_response

            return "I apologize, but I couldn't process this request due a problem. Please check if your query is clearly stated or try rephrasing it."
    
    except Exception as e:
        # Return specific error message for math processing
        return f"Error processing your query: {str(e)}"