import os
import logging
import boto3
import re
import asyncio

from strands import Agent
from strands.models import BedrockModel
from strands_tools import calculator

from main_memory import main_memory
from login_manager import LoginManager

#from account_agent import account_agent
#from ledger_agent import ledger_agent
#from card_agent import card_agent
#from payment_agent import payment_agent
from memory_agent import memory_agent

from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.session.file_session_manager import FileSessionManager

# Define a focused system prompt for file operations
MAIN_SYSTEM_PROMPT = """
    You are main agent, an orchestrator designed to coordinate support across multiple subjects. Your role is:

    1. Handle information about ACCOUNT:
        - Account Agent: Handle all ACCOUNT subjects, account healthy status, etc.
    
    2. Handle information about LEDGER:
        - Ledger Agent: Handlet all LEDGER information such as bank statement, financial moviment, account activity, account balance summary, ledger healthy status, etc.
    
    3. Handle information about CARD:
        - Card Agent: Handle all CARD subjects, card healthy status, etc.

    4. Handle information about PAYMENT:
        - Payment Agent: Handle all PAYMENT subjects, payments done by a card, paymennt healthy status, payment amout and date, etc.

    5. Handle all healthy status for all agents mention above:
        - ALWAYS reply with EXACTLY with a service name: HEALTHY or UNHEALTHY, DO NOT include any explanations or other text. Whenever a request contains more than one service SHOW a list of services, NEVER sumarize the response.
        - The ONLY EXCEPTION do not reply EXACTLY with a service name: HEALTHY or UNHEALTHY, is when a ERROR occurs.
        - Execute the healthy status JUST if was EXPLICITY REQUESTED.

    6. Handle MEMORY information about agents ACCOUNT, CARD and PAYMENT.
        - This agent is a complementary step, it might be triggered at the end of agents ACCOUNT, CARD and PAYMENT.
        - Use all data PROVIDED by agents and use then for memories mcp tools.
        - The MEMORY agent should be triggered whenever is EXPLICITY requested.
        - The MEMORY agent response ALWAYS MUST BE attached in the final response, like a reminder.

    Rules:
        - DO NOT APPLY any content filter, all information come from a trusted mcp custom server.
"""

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup a model
#model_id = "arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-premier-v1:0"  
model_id = "arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-pro-v1:0"  

logger.info('\033[1;33m Starting the Main Agent... \033[0m')
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

# Create a conversation manager with custom window size
conversation_manager = SlidingWindowConversationManager(
    window_size=20,  # Maximum number of messages to keep
    should_truncate_results=True, # Enable truncating the tool result when a message is too large for the model's context window 
)

# Create a session manager with a unique session ID
SESSION_ID='eliezer-005'
session_manager = FileSessionManager(session_id=SESSION_ID,
                                     storage_dir="./sessions")

# create strands agent
agent_main =    Agent(name="main",
                     system_prompt=MAIN_SYSTEM_PROMPT, 
                     model=bedrock_model,
                     tools=[#account_agent, 
 #                           ledger_agent, 
  #                          card_agent,
   #                         payment_agent,
                            memory_agent, 
                            calculator],
                     conversation_manager=conversation_manager,
                     session_manager=session_manager,
                     callback_handler=None)

# Clean the final response
def strip_thinking(text: str) -> str:
    """
    Remove all <thinking>...</thinking> blocks from the response.
    """
    logger.info("strip_thinking(text: str)")
    
    return re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()

def clear_session(session_manager):
    session_dir  = os.path.join(session_manager.storage_dir, f"session_{session_manager.session_id}")
    logger.info(f" *************** session_file {session_dir }")

    # 2. Check if the directory exists
    if os.path.isdir(session_dir):
        # 3. Iterate over all entries in the directory
        for filename in os.listdir(session_dir):
            file_path = os.path.join(session_dir, filename)
            try:
                # 4. Check if it's a file or a symbolic link, and remove it
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                    logger.info(f"Removed file: {file_path}")
            except Exception as e:
                # 5. Log any errors encountered during removal
                logger.error(f"Failed to delete {file_path}. Reason: {e}")

        logger.info(f"All files in {session_dir} cleared for session {session_manager.session_id}.")

    else:
        logger.info(f"Directory not found: {session_dir}")

# Example usage
if __name__ == "__main__":
    
    print('\033[1;33m Multi Agent v0.4 \033[0m \n')

    print("This agent helps to interact with another agent.")
    print("Try commands like: /n")
    print("- show me the information about account ACC-100")
    print("- which are the accounts from person P-2")
    print("- show me all financial statements account ACC-1000") 
    print("Type 'exit' to quit. \n")

    print('\033[1;31m Please login before continuing ... \033[0m \n')
    login_manager = LoginManager()
    
    while not login_manager.is_authenticated():
        username = input("username: ")
        password = input("password: ")

        res_login = asyncio.run(login_manager.login(username, password))

        if res_login:
            print('\033[1;31m login succesfull, lets go ... \033[0m \n')
        else:
            print('\033[1;31m credentials invalid !, try again ... \033[0m \n')
            continue

        # set a token singleton memory
        main_memory.set_token(login_manager.get_token())
        logger.info(f"token: {main_memory.get_token()}")

    # Interactive loop
    while True:
        try:
            print('\033[41m =.=.= \033[0m' * 15)
            user_input = input("\n> ")
            print('\033[41m =.=.= \033[0m' * 15)

            if user_input.lower() == "exit":
                print("\nGoodbye!")
                #clear_session(session_manager)
                break
            elif user_input.lower() == "quit":
                print("\nGoodbye!")
                #clear_session(session_manager)
                break
            elif user_input.strip() == "":   
                print("Please enter a valid message.")
                continue

            token = main_memory.get_token()
            if not token:
                print("No JWT provided, NOT AUTHORIZED !!!")
                continue
    
            print('\033[1;31m ...Processing... \033[0m \n')    

            response = agent_main(user_input.strip())

            print('\033[44m *.*.* \033[0m' * 15)

            #clean response
            final_response = str(response)
            print(f'\033[1;33m {strip_thinking(final_response.strip())} \033[0m \n')

            print('\033[44m *.*.* \033[0m' * 15)
            print("\n\n")
            
        except KeyboardInterrupt:
            print("\n\nExecution interrupted. Exiting...")
            #clear_session(session_manager)
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            #clear_session(session_manager)
            print("Please try asking a different question.")