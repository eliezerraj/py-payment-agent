import boto3

from strands import Agent
from strands.models import BedrockModel

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

# Create an agent using the BedrockModel instance
agent = Agent(model=bedrock_model)

def run_agent(query):
    """Process a user query"""
    response = agent(f"{query}")
    print(response)

if __name__ == "__main__":
    # Print welcome message
    print("\n Agent test llm model \n")
    print("This agent helps to interact with a llm model.")
    print("Try commands like:")
    print("- \"who is mickey mouse ?\"")
    print("\nType your request below or 'exit' to quit:")

    # Interactive loop
    while True:
        try:
            user_input = input("\n> ")
            if user_input.lower() in ["exit", "quit"]:
                print("\nGoodbye!")
                break
            
            if not user_input.strip():
                continue
                
            # Process the input through the knowledge base agent
            print("Processing...")
            run_agent(user_input)
            
        except KeyboardInterrupt:
            print("\n\nExecution interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")