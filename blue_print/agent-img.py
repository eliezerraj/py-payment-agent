import boto3

from pydantic import BaseModel
from strands import Agent
from strands.models import BedrockModel
from typing import Optional

def main():

    # Create boto3 session
    session = boto3.Session(
        region_name='us-east-2',
    )

    model_id = "arn:aws:bedrock:us-east-2:908671954593:inference-profile/us.amazon.nova-premier-v1:0"  

    bedrock_model = BedrockModel(
        model_id=model_id,
        boto_session=session,
    )

    class PersonInfo(BaseModel):
        name: Optional[str]
        age: Optional[int]
        occupation: Optional[str]

    agent = Agent(model=bedrock_model)

    result = agent.structured_output(
        PersonInfo,
        "John Smith is a 30-year-old software engineer"
    )

    print(f"Name: {result.name}")      # "John Smith"
    print(f"Age: {result.age}")        # 30
    print(f"Job: {result.occupation}") # "software engineer"

    class CNHInfo(BaseModel):
        nome: Optional[str]
        cpf: Optional[str]
        validade: Optional[str]

    with open("./img/juliana_cnh.pdf", "rb") as fp:
        document_bytes = fp.read()

    result = agent.structured_output(
        CNHInfo,
        [
            {"text": "Extract the fields 'nome' 'cpf' and 'validade' from this document."},
            {
                "document": {
                    "format": "pdf",
                    "name": "juliana_cnh",
                    "source": {
                        "bytes": document_bytes,
                    },
                },
            },
        ]
    )

if __name__ == "__main__":
    main()