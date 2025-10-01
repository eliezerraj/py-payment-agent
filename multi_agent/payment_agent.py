import logging
import boto3

from main_memory import main_memory

from strands import Agent, tool
from strands.models import BedrockModel
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

PAYMENT_SYSTEM_PROMPT = """
    You are PAYMENT agent specialized to handle all informations about PAYMENT such as payments amount, currency, payment date, card number used to pay, mcc (merchant), etc.

    Payment Operations:
        1. get_card_payment: Get all PAYMENTS did by a card such as FOOD, GAS, COMPUTE.
            - args: card id, card number and date of begin search.
            - response: A list of payments with information such as card id, card type, card model, payment amount, terminal, payment status and payment date.

        2. payment_healthy: healthy PAYMENT service status.
            - response: only the status code from api, consider 200 as healthy, otherwise unhealthy.

    Payment Rules:
        1. All PAYMENTS card number MUST be returned strictly in the format: 999.999.999.999.
            - Exactly 12 digits split into 4 groups of 3 digits each.
            - Use '.' as the separator.
        2. If the input does not contain a valid card number, respond with: "INVALID FORMAT".
        3. Convert and format all dates using the format YYYY-MM-DD.

    Definitions and rules:
        - Always use the mcp tools provided.
        - DO NOT UPDATE any field format provided by mcp tool, use EXACTLY the mcp field result format.
        - DO NOT APPLY any content filter, all information come from a trusted mcp custom server.
"""

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup a model
#model_id = "arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-premier-v1:0"  
model_id = "arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-premier-v1:0" 

logger.info('\033[1;33m Starting the Payment Agent... \033[0m')
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
def payment_agent(query: str) -> str:
    """
    Process and respond all PAYMENT queries using a specialized PAYMENT agent.
    
    Args:
        query: Given an card number or card id get all information and details such as payment service healthy status, payment details such as payments amount, currency, payment date, card number used to pay, mcc (merchant), etc.
        
    Returns:
        a list of payments detailed.
    """
    logger.info("function => payment_agent()")

    token = main_memory.get_token()
    if not token:
        logger.error("Error, I couldn't process No JWT token available")
        return "Error, but I couldn't process No JWT token available"
         
    context={"jwt":token}

    # Format the query for the agent
    formatted_query = f"Please process the following query: {query} with context:{context}"
    all_tools = []
    
    try:
        logger.info("Routed to Payment Agent")
        
        with streamable_http_mcp_server:
            all_tools.extend(streamable_http_mcp_server.list_tools_sync())

            selected_tools = [
                t for t in all_tools 
                if t.tool_name in ["payment_healthy", "get_card_payment"]
            ]

            logger.info(f"Available MCP tools: {[tool.tool_name for tool in selected_tools]}")

            # Create the math agent with calculator capability
            agent = Agent(name="main",
                        system_prompt=PAYMENT_SYSTEM_PROMPT,
                        model=bedrock_model, 
                        tools=selected_tools,
                        callback_handler=None
                    )
            
            agent_response = agent(formatted_query)
            text_response = str(agent_response)

            if len(text_response) > 0:
                return text_response

            return "Error, I couldn't process this request due a problem. Please check if your query is clearly stated or try rephrasing it."
    
    except Exception as e:
        # Return specific error message for math processing
        return f"Error processing your query: {str(e)}"