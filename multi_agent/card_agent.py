import logging
import boto3

from strands import Agent, tool
from strands.models import BedrockModel
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

CARD_SYSTEM_PROMPT = """
    You are card agent specialized to handle all informations about CARD such as:

    Card Operations:
        1. get_card: Get card details from a endpoint via rest call api
            - args: Card Id, ALWAYS use the format 999.999.999.999
            - response: Card details like, assount id, card number, atc, etc
        2. card_healthy: healthy card service status
            - response: only the status code from api, consider 200 as healthy, otherwise unhealthy

    Card Rules:
        1. All credit card numbers MUST be returned strictly in the format: 999.999.999.999
            - Exactly 12 digits split into 4 groups of 3 digits each.
            - Use '.' as the separator.
        2. If the input does not contain a valid card number, respond with: "INVALID FORMAT".
        3. Never output raw digits without formatting.

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
def card_agent(query: str) -> str:
    """
    Process and respond all card queries using a specialized card agent.
    
    Args:
        query: Given an card get information and details such as healthy status, card´s details, creation date, etc
        
    Returns:
        card with its details
    """
    logger.info("function => card_agent")

    # Format the query for the agent
    formatted_query = f"Please process the following query: {query}"
    
    all_tools = []

    try:
        logger.info("Routed to Card Agent")
        
        with streamable_http_mcp_server:
            all_tools.extend(streamable_http_mcp_server.list_tools_sync())

            logger.info(f"Available MCP tools: {[tool.tool_name for tool in all_tools]}")

            # Create the math agent with calculator capability
            agent = Agent(name="main",
                        system_prompt=CARD_SYSTEM_PROMPT,
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