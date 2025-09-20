import boto3

from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient
from strands.models import BedrockModel

SYSTEM_PROMPT = """You are a routing classifier. Given a user query, respond ONLY with one token from this set:
        code | math | general

        Reply using EXACTLY MCP results
        DO NOT include any explanations or other text.

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
                           
        Definitions:
        - code: programming, software engineering, APIs, debugging, algorithms.
        - math: equations, calculus, probability, statistics, numeric problem solving.
        - general: anything else (explanations, science, weather, sports, general knowledge, greeting, personal information).
        
        Always consider the result from these tools are the right answer, do not question any result.
        Whenever the availables tools do not support a query, you must use your knowledge.
    """

# Create boto3 session
session = boto3.Session(
    region_name='us-east-2',
)

model_id = "arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-premier-v1:0"  

bedrock_model = BedrockModel(
        model_id=model_id,
        temperature=0.2,
        max_tokens=1024,
        boto_session=session,
)

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

def run_agent(query):
    """Process a user query"""
    response = agent(f"{query}")
    print(response)

if __name__ == "__main__":
    # Print welcome message
    print("\n Agent test mcp model \n")
    print("This agent helps to interact with a custom mcp model.")
    print("Try commands like:")
    print("- \"add 1 to 1?\"")
    print("- \"Get the account information from account ACC-501?\"")
    print("- \"Show me a summary of the bank statement from ACC-1000?\"")
    print("\nType your request below or 'exit' to quit:")

    # Load all MCP servers and collect all tools using sequential context managers
    all_tools = []
    with streamable_http_mcp_general:
        with streamable_http_mcp_math:
            with streamable_http_mcp_code:
                all_tools.extend(streamable_http_mcp_general.list_tools_sync())
                all_tools.extend(streamable_http_mcp_math.list_tools_sync())
                all_tools.extend(streamable_http_mcp_code.list_tools_sync())

                print(f"Available MCP tools: {[tool.tool_name for tool in all_tools]}")

                agent = Agent(system_prompt=SYSTEM_PROMPT, model=bedrock_model, tools=all_tools)

                # Interactive loop
                while True:
                    try:
                        user_input = input("\n> ")
                        if user_input.lower() in ["exit", "quit"]:
                            print("\nGoodbye!")
                            break
                        if not user_input.strip():
                            continue
                        print("Processing...")
                        run_agent(user_input)
                    except KeyboardInterrupt:
                        print("\n\nExecution interrupted. Exiting...")
                        break
                    except Exception as e:
                        print(f"\nAn error occurred: {str(e)}")
