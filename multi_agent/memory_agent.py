import logging
import boto3

from main_memory import main_memory

from strands import Agent, tool
from strands.models import BedrockModel
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

MEMORY_SYSTEM_PROMPT = """
    You are memory agent specialized to handle(STORE and RETRIEVE) all MEMORIES of a memory graph database.

    Memory Activity :
        1. store_memory_graph_account: Store all account information and its relations in memory graph account
            - args:
                - account: account identificator
                - person: person identificator
                - relations: relation between account and person, this relation MUST BE 'HAS'
            - response: 
                - JUST a confirmation if the data aws store with successful or failed

        2. retrieve_memory_graph_account: Retrive from memory graph all account informations
            - args:
                - account: account identificator
            - response:
                - list: list of person_id (owner) of account

        3. store_memory_graph_card: Store all card information and its relation in memory graph account
            - args
                - card: card identificator
                - account: account identificator
                - relations: relation between card and account, this relation MUST BE 'ISSUED'
            - response: 
                - JUST a confirmation if the data aws store with successful or failed 

    Definitions and rules:
        - The RETRIEVE choice is ALWAYS triggered when you receive a EXPLICITY requesr in a past tense question, such words as last, previous, latter, final, late. etc
    """

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Starting the Memory Agent...")

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
def memory_agent(query: str) -> str:
    """
    Process and respond all request and queries using a memory graph knowledge.
    
    Args:
        query: requests knowledges and memories stored
        
    Returns:
        a memory from memory graph database
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

            logger.info(f"Available MCP tools: {[tool.tool_name for tool in all_tools]}")

            # Create the math agent with calculator capability
            agent = Agent(name="main",
                        system_prompt=MEMORY_SYSTEM_PROMPT,
                        model=bedrock_model, 
                        tools=all_tools,
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