import boto3
import re
import logging

from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient
from strands.models import BedrockModel

SYSTEM_PROMPT = """You are a routing classifier. Given a user query, respond ONLY with one token from this set:
        code | math | general

        You have access to MCP tools bellow:

        For math:
        1. add: add two numbers
        - args: a (float) the first number and b (float) the second number
        2. sub: subtract two numbers
        - args: a (float) the first number and b (float) the second number
        3. multiple: multiplication two numbers
        - args: a (float) the first number and b (float) the second number
        4. divide: divide two numbers
        - args: a (float) the first number and b (float) the second number

        For general:
        1. get_weather: Get current weather information for a given location.
            - args: location: The city name to get weather for
        2. get_current_time: Get current date and time.
        3. save_note: Save a text note for the user to a file.
        - args: filename (name of the file to save without extension) and content (The text content to save)

        For code:
        1. get_account: Get account details from a endpoint via rest call api
        - args: Account Id
        2. get_account_statement: Get all account bank statementor or moviments from a endpoint via rest call api
        - args: Account Id
        3. store_memory_graph_account: Store the account´s data into a memory graph
        - args: Account Id, Person Id, Relation HAS
        4. retrieve_memory_graph_account: Retrieve the account´s data from memory graph
        - args: Account Id

        Definitions:
        - code: programming, software engineering, APIs, debugging, algorithms.
        - math: equations, calculus, probability, statistics, numeric problem solving.
        - general: anything else (explanations, science, weather, sports, general knowledge, greeting, personal information).

        Handling Response:
        - code: Together with the final response, also return the reponse JSON object from MCP tool.
        
        Reply ALWAYS using EXACTLY MCP tools results even the result is WRONG, do not assume that your knowledge base is right, the FINAL answer is always come from MCP tools.

        Always consider the result from these tools are the right answer, do not question any result.
        Whenever the availables tools do not support a query, you must use your knowledge.
    """

MEMORY_SYSTEM_PROMPT="""
        You are a knowledge base assistant focusing ONLY on classifying user queries.
        Your task is to determine whether a user query requires STORING information to a knowledge base,
        RETRIEVING information from a knowledge base or SKIP when a user query is not related with the code subjects.

        Reply with EXACTLY ONE WORD - either "store","retrieve" or "skip".
        DO NOT include any explanations or other text.

        The RETRIEVE choice is ALWAYS regard a past tense question, such words as last, previous, latter, final, late. etc

        Examples:
        - "get the account information from account ACC-501" -> "store"
        - "give me all information about account ACC-001" -> "store"
        - "remember me the last account searched" -> "retrieve"
        - "show me the last account" -> "retrieve"

        Only respond with "store" or "retrieve" or "skip" - no explanation, prefix, or any other text.
        """

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create boto3 session
session = boto3.Session(
    region_name='us-east-2',
)

model_id = "arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-premier-v1:0"  

bedrock_model = BedrockModel(
        model_id=model_id,
        temperature=0.0,
        #max_tokens=1024,
        boto_session=session,
)

# create strands agent
agent_memory = Agent(name="memory",
                     system_prompt=MEMORY_SYSTEM_PROMPT, 
                     model=bedrock_model,
                     callback_handler=None,)

# load mcp servers
def create_streamable_http_mcp_general():
    return streamablehttp_client("http://localhost:9000/mcp")

streamable_http_mcp_general = MCPClient(create_streamable_http_mcp_general)

def create_streamable_http_mcp_math():
    return streamablehttp_client("http://localhost:9001/mcp")

streamable_http_mcp_math = MCPClient(create_streamable_http_mcp_math)

def create_streamable_http_mcp_code():
    return streamablehttp_client("http://localhost:9002/mcp")

streamable_http_mcp_code = MCPClient(create_streamable_http_mcp_code)

# Clean the final response
def strip_thinking(text: str) -> str:
    """
    Remove all <thinking>...</thinking> blocks from the response.
    """
    logger.info("strip_thinking(text: str)")
    
    return re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()

# Choose how to handle the memory
def determine_action_memory(query):
    """Determine if the query is a store or retrieve action."""

    logger.info("determine_action(agent, query)")

    # Call the main agent
    response = agent_memory(f"Query: {query}")
    
    # Clean and extract the action
    action_memory = str(response).lower().strip()
    
    # Check the memory decision
    if "store" in action_memory:
        return "store"
    elif "retrieve":
        return "retrieve"
    else:
        return "skip"

# Run thwe main agent    
def run_agent(query) -> str:
    """Process a user query"""
    logger.info("run_agent(query)")

    # Determine the memory action (store, retrieve or skip)
    action = determine_action_memory(query)
    logger.info(f"action: {action} \n")

    if action == 'store':
        s=""
    elif action == 'retrieve':
        s =""
    else:
        s=""

    # Call the agent
    response = agent(f"{query}")
    logger.info(f"response: {response} \n")

    return response

if __name__ == "__main__":
    # Print welcome message
    print("\n Agent test mcp model with memory graph v0.1 \n")
    print("This agent helps to interact with a custom mcp model.")
    print("Try commands like:")
    print("- \"add 1 to 1\"")
    print("- \"get the account information from account ACC-501\"")
    print("- \"Show me a summary of the bank statement from ACC-1000\"")
    print("- \"add a account graph with this informations, person_id P-005, account_id AC-005.1, description HAS\"")
    print("- \"retrieve the memory from account_id AC-005.1\"")  
    # get the account information from account ACC-3 and store then into memory graph
    print("\nType your request below or 'exit' to quit: \n")

    # Load all MCP servers and collect all tools using sequential context managers
    all_tools = []
    agent = ""

    with streamable_http_mcp_general:
        with streamable_http_mcp_math:
            with streamable_http_mcp_code:
                all_tools.extend(streamable_http_mcp_general.list_tools_sync())
                all_tools.extend(streamable_http_mcp_math.list_tools_sync())
                all_tools.extend(streamable_http_mcp_code.list_tools_sync())

                logger.info(f"Available MCP tools: {[tool.tool_name for tool in all_tools]}")

                agent = Agent(name="main", 
                              system_prompt=SYSTEM_PROMPT, 
                              model=bedrock_model, 
                              tools=all_tools,
                              callback_handler=None,
                              )

                # Interactive loop
                while True:
                    try:
                        user_input = input("\n> ")
                        if user_input.lower() in ["exit", "quit"]:
                            print("\nGoodbye!")
                            break
                        if not user_input.strip():
                            continue
                        
                        print("Processing... \n")
                        response = run_agent(user_input)

                        print("-.-.-" * 10)
                        print(strip_thinking( str(response).lower().strip()) )
                        print("-.-.-" * 10)

                    except KeyboardInterrupt:
                        print("\n\nExecution interrupted. Exiting...")
                        break
                    except Exception as e:
                        print(f"\nAn error occurred: {str(e)}")
