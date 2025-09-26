import logging
import boto3
import re

from strands import Agent
from strands.models import BedrockModel
from strands_tools import calculator

from main_memory import main_memory

from account_agent import account_agent
from ledger_agent import ledger_agent
from card_agent import card_agent

from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.session.file_session_manager import FileSessionManager

# Define a focused system prompt for file operations
MAIN_SYSTEM_PROMPT = """
    You are main agent, an orchestrator designed to coordinate support across multiple subjects. Your role is:

    1. Handle information about ACCOUNT:
        - Account Agent: Handle all ACCOUNT subjects, healthy, etc
    
    2. Handle information about LEDGER:
        - Ledger Agent: Handlet all LEDGER information such as bank statement, financial moviment, account activity, balance summary, healthy, etc
    
    3. Handle information about CARD:
        - Card Agent: Handle all CARD subjects, healthy, etc.
    
    4. Handle all healthy status for all agents mention above 
        - ALWAYS reply with EXACTLY with a service name: HEALTHY or UNHEALTHY, DO NOT include any explanations or other text. Whenever a request contains more than one service SHOW a list of services, NEVER sumarize the response.
        - The ONLY EXCEPTION do not reply EXACTLY with a service name: HEALTHY or UNHEALTHY, is when a ERROR occurs.

    Always confirm your understanding before routing to ensure accurate assistance.
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

# Create a conversation manager with custom window size
conversation_manager = SlidingWindowConversationManager(
    window_size=20,  # Maximum number of messages to keep
    should_truncate_results=True, # Enable truncating the tool result when a message is too large for the model's context window 
)

# Create a session manager with a unique session ID
session_manager = FileSessionManager(session_id="eliezer-session-03",
                                     storage_dir="./sessions")

# create strands agent
agent_main =    Agent(name="main",
                     system_prompt=MAIN_SYSTEM_PROMPT, 
                     model=bedrock_model,
                     tools=[account_agent, 
                            ledger_agent, 
                            card_agent, 
                            calculator],
                     conversation_manager=conversation_manager,
                     session_manager=session_manager,
                     callback_handler=None)

# set a token singleton memory 
TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl91c2UiOiJhY2Nlc3MiLCJpc3MiOiJnby1vYXV0aC1sYW1iZGEiLCJ2ZXJzaW9uIjoiMi4xIiwiand0X2lkIjoiZjg1NmQyZTgtZGEzMy00ZGIyLWEwOTctOWU2ZTU3NWMzNDVkIiwidXNlcm5hbWUiOiJ1c2VyLTAzIiwidGllciI6InRpZXItMDMiLCJhcGlfYWNjZXNzX2tleSI6IkFQSV9BQ0NFU1NfS0VZX1VTRVJfMDMiLCJzY29wZSI6WyJ0ZXN0LnJlYWQiLCJ0ZXN0LndyaXRlIiwiYWRtaW4iXSwiZXhwIjoxNzU5MDE0ODIzfQ.TMut_pM6inWcm02j7dim11ukD1P7jqQ_SkYwDG0GcGg7cvhPvgSiKOa9UFaqbrKAEGRcHG8Q7bFLFbX0v9oht2CMcKrNUZWdqScY3LdB-xaWLSAyaWDjYHfnm_rc_DZ7YOD3OjH5KaFMFL5OE0K-n1AhwGcYTSQLSLSxyOIe7jWJ_hiIsSDpb-kV_wejzwotk4mgM2x9A7fCMIMibJCRSua6biCfF99mNrJT3RmIyzIUrI_1PlLFIIrloviTyXrvSAwmAb8KE2pJkO_y0I0fNvbTx5-4IXvjzhv6BhyiLvJfdP488D_tyGucp9N9zAr7wQ-iHC5xzqrsd9aYLlKUN-k9E13fMWg-X3mbyRC-7N8oHE2K99AsyvK0DruepP9n2pCKadgbvNLA9t_yD9oxSmxGG27IAXCKPiqQmsUYQzUjuTE7iwYfIgAiZHzdHeptr6Yh9G5HG3w_KTDBOTklemhfMw9eJjkOTL0uKPk-DkuyC0O_-nYSu7TC4uPnAEtaC_87Bbpo__z_NVteBVvJ7b1eRY2_IB8udSpSRpiI0ogEWm5sc7IL61kKyCqLpu6vRDxewFnhyW83x16iZrRsAGPLiDcIto3gLqm_MPKqpPcbf4cxCfeKuAbtgPmMN19mD46a4lOWJIQ8Ds2kuwK8wJ2wdb4u0d01jtRBDoFHq2E"
main_memory.set_token(TOKEN)

# Clean the final response
def strip_thinking(text: str) -> str:
    """
    Remove all <thinking>...</thinking> blocks from the response.
    """
    logger.info("strip_thinking(text: str)")
    
    return re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()

# Example usage
if __name__ == "__main__":
    
    print('\033[1;31m Multi Agent v0.4 \033[0m \n')

    print("This agent helps to interact with another agent.")
    print("Try commands like: /n")
    print("- show me the information about account ACC-100")
    print("- which are the accounts from person P-2")
    print("- show me all financial statements account ACC-1000") 
    print("Type 'exit' to quit.")

    # Interactive loop
    while True:
        try:
            print('\033[41m =.=.= \033[0m' * 15)
            user_input = input("\n> ")
            print('\033[41m =.=.= \033[0m' * 15)

            if user_input.lower() == "exit":
                print("\nGoodbye!")
                break
            elif user_input.lower() == "quit":
                print("\nGoodbye!")
                break
            elif user_input.strip() == "":   
                print("Please enter a valid message.")
                continue

            token = main_memory.get_token()
            if not token:
                print("No JWT provided, NOT AUTHORIZED !!!")
                continue
    
            print('\033[1;31m  Processing... \033[0m \n')
            response = agent_main(user_input.strip())

            print('\033[44m *.*.* \033[0m' * 15)
            final_response = str(response)
            print(strip_thinking( final_response.lower().strip()) )

            print('\033[44m *.*.* \033[0m' * 15)
            print("\n\n")
            
        except KeyboardInterrupt:
            print("\n\nExecution interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            print("Please try asking a different question.")