import logging
import boto3

from main_memory import main_memory

from strands import Agent, tool
from strands.models import BedrockModel
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

ACCOUNT_SYSTEM_PROMPT = """
    You are ACCOUNT agent specialized to handle all informations about ACCOUNT.

    Account Operations:
        1. get_account: get account details such as account id (account_id), owner account (person_id), date of creation (created_at) from a given account (account_id)
            - args: 
                - account: account identificator (account_id).
            - response: 
                - account details like, account id (account_id), person id (owner account), date of creation (created_at).
        
        2. get_accounts_from_person: get all accounts associated/belongs a given person (person_id).
            - args: 
                - person: person identificator (person_id).
            - reponse: 
                - list: List of accounts owned/belongs by a given person (person id).
        
        3. account_healthy: check the healthy status ACCOUNT service.       
            - response:
                - content: all information about ACCOUNT service health status and enviroment variables. 
            Healthy Rule::
                - This tool must be triggered ONLY with a EXPLICITY requested.
                - return only the status code, consider 200 as healthy, otherwise unhealthy.

        4. create_accont: Create an account.
            - args: 
                - account: account identificator (account_id)
                - person: person identificator (person_id).
            - response: 
                - account: account details such as account id (account_id), person id (owner account), date of creation (created_at).       

    Definitions and Rules:
        - Always use the mcp tools provided.
        - The account pattern should be ACC-### or ACC-###.###
        - The person pattern should be P-### or P-###.###
        - USE EXACTLY the fields provided by query, DO NOT PARSE, DO NOT STRIP OF '.' or '-' or FORMAT.
        - USE EXACTLY the fields names provided by json response. eg: account_id, person_id, etc.
        - DO NOT UPDATE any field format provided by mcp tool, use EXACTLY the mcp field result format.
"""

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup a model
#model_id = lite pro premier
model_id = "arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-pro-v1:0"  

logger.info('\033[1;33m Starting the Account Agent... \033[0m')
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
def account_agent(query: str) -> str:
    """
    Process and respond all ACCOUNT queries using a specialized ACCOUNT agent.
    
    Args:
        query: Given account, create account, get account informations and details, and check account healthy status.
        
    Returns:
        an account with all details.
    """
    logger.info("function => account_agent")
   
    token = main_memory.get_token()
    if not token:
        logger.error("Error, I couldn't process No JWT token available")
        return "Error, I couldn't process No JWT token available"
         
    context={"jwt":token}

    try:
        logger.info("Routed to Account Agent")

        # Format the query for the agent
        formatted_query = f"Please process the following query: {query} with context:{context} and extract structured information"
        all_tools = []
         
        with streamable_http_mcp_server:
            all_tools.extend(streamable_http_mcp_server.list_tools_sync())

            selected_tools = [
                t for t in all_tools 
                if t.tool_name in ["account_healthy", 
                                   "get_account",
                                   "create_account", 
                                   "get_account_from_person"]
            ]

            logger.info(f"Available MCP tools: {[tool.tool_name for tool in selected_tools]}")

            # Create the math agent with calculator capability
            agent = Agent(name="main",
                        system_prompt=ACCOUNT_SYSTEM_PROMPT,
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