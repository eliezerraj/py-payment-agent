import logging
import boto3

from main_memory import main_memory

from strands import Agent, tool
from strands.models import BedrockModel
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

MEMORY_SYSTEM_PROMPT = """
    You are memory agent specialized to handle(STORE) all MEMORIES of a memory graph database.

    Memory Activity :
        1. store_account_memory: Store the ACCOUNT its relation with PERSON in memory graph account.
            - args:
                - account: account id (account_id)
                - person: person id (person_id).
                - relations: relation between account and person, this relation MUST BE 'HAS'.
            - response: 
                - JUST a confirmation if the data aws store with successful or failed.

        2. store_card_memory: Store the CARD its relation with ACCOUNT in memory graph account.
            - args
                - card: card number, card id, type, model.
                - account: account id.
                - relations: relation between card and account, this relation MUST BE 'ISSUED'.
            - response: 
                - JUST a confirmation if the data aws store with successful or failed.

        3. store_payment_memory: Store the PAYMENT its relation with CARD in memory graph account.
            - args
                - payment: payment id, currency, amount, mcc, payment date, status.
                - card: card number.
                - relations: relation between card and payment, this relation MUST BE 'PAY'.
            - response: 
                - JUST a confirmation if the data aws store with successful or failed.

    Definitions and rules:
        - The all STORE choice is ALWAYS triggered when you receive a EXPLICITY request.
    """

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup a model
#model_id = lite pro premier 
model_id = "arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-premier-v1:0"  

logger.info('\033[1;33m Starting the Memory Agent... \033[0m')
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
def memory_agent(query: str) -> str:
    """
    Process and respond all memory request and queries using a memory graph knowledge.
    
    Args:
        query: requests knowledges and memories stored.
        
    Returns:
        a memory from memory graph database.
    """
    logger.info("function => memory_agent()")
   
    token = main_memory.get_token()
    if not token:
        logger.error("Error, I couldn't process No JWT token available")
        return "Error, I couldn't process No JWT token available"
         
    context={"jwt":token}

    # Format the query for the agent
    formatted_query = f"Please process the following query: {query} with context:{context}"
    all_tools = []
 
    try:
        logger.info("Routed to Memory Agent")
        
        with streamable_http_mcp_server:
            all_tools.extend(streamable_http_mcp_server.list_tools_sync())

            selected_tools = [
                t for t in all_tools 
                if t.tool_name in ["store_account_memory", "store_card_memory", "store_payment_memory"]
            ]

            logger.info(f"Available MCP tools: {[tool.tool_name for tool in selected_tools]}")

            # Create the math agent with calculator capability
            agent = Agent(name="main",
                        system_prompt=MEMORY_SYSTEM_PROMPT,
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