# py-payment-agent
py-payment-agent

# create venv
python3 -m venv .venv

# activate
source .venv/bin/activate

# install requirements
pip install -r requirements.txt

pip install --force-reinstall strands-agents-tools

# run
python3 agent.py

# otel env
export OTEL_EXPORTER_OTLP_ENDPOINT="localhost:4317"

# test local otel
kubectl port-forward svc/arch-eks-01-02-otel-collector-collector  4317:4317

HEALTH-ok
check the current health status of ACCOUNT services and show the result
check the current health status of LEDGER services and show the result
check the current health status of CARD and ACCOUNT services and show the result
check the current health status of all services avaiable and show the result

ACCOUNT - OK
create an account with id ACC-302.201 and a person P-302.201
create 3 accounts with id from ACC-800.107 and a from person P-800.107 respectively
create 3 accounts with id from ACC-800.110 but all of then must belongs for same person P-800.110

show me the details of account ACC-302.250 
show me the current details of account ACC-4.000.002 
get all details of account ACC-4.000.003 and ACC-4.000.004
show me the infos of account ACC-200, ACC-201

ACCOUNT-PERSON - OK
show me the P-750 person's account
show me the current accounts of person P-751
which are the accounts from person P-500
show me all accounts of person P-721 and P-722
check the current the accounts belongs to a person P-723

LEDGER
make a transaction type DEPOSIT, amount 2000 currency BRL over account ACC-301.002
make a DEPOSIT, amount BRL 900.00 over account ACC-302.201

show me the bank statement of account ACC-302.201
show me all financial statements account ACC-4.000.000
which are the account activity of account ACC-4.000.003
show me the detailed balance summary of account ACC-4.000.003

CARD 
show me the data of card 111.004.000.004
get all details of card 111.111.004.002
get all details of cards 111.111.004.000 and 111.111.004.004
create a card number 333.000.302.201 type DEBIT model CHIP holder eliezer-jr and associated with an account ACC-302.201


Playbook

create an account with id ACC-300.100 and a person P-300.100 and after create a card number 333.000.300.000 type DEBIT model CHIP holder eliezer and associated with an account ACC-300.100
create an account with id ACC-300.101 and a person P-300.101 and after create 3 cards number from 333.000.300.101 , all cards type DEBIT model CHIP holder juliana and associated with an account ACC-300.101


PAYMENT
show me the payments of card 111.004.000.000 after 2025-09-21 
show me the payments of card 111.004.000.004 after 2025-09-21  

make a payment over a card 111.004.000.004 CREDIT, terminal TERM-2, for a GAS with amount amount BRL 310.00

MEMORY
store the info: "id": 1532, "account_id": "ACC-4.000.000", "person_id": "P-4.000.000", "created_at": "2025-09-30T16:28:07.925031Z"

store the info: "id": 1388, "fk_account_id": 1532,"account_id": "ACC-4.000.000", "card_number": "111.004.000.000", "holder": "holder-505", "type": "DEBIT", "model": "CHIP", "status": "ISSUED", "expired_at": "2030-09-30T17:22:55.496725821Z", "created_at": "2025-09-30T17:22:55.496725686Z","tenant_id": "TENANT-1"

store the info: Account ID: ACC-4.000.000 - Payment ID: 1054304   - Card number: 111.004.000.000  - Card type: CREDIT  - Card model: CHIP  - MCC: FOOD  - Status: AUTHORIZATION:OK  - Currency: BRL  - Amount: 12.4  - Payment at: 2025-09-30T15:50:28.722085Z  - Terminal: TERM-1  - Created at: 0001-01-01T00:00:00Z - Payment ID: 1054305  - Card number: 111.004.000.000  - Card type: CREDIT  - Card model: CHIP  - MCC: GAS  - Status: AUTHORIZATION:OK  - Currency: BRL  - Amount: 200  - Payment at: 2025-09-30T15:50:53.123774Z  - Terminal: TERM-1  - Created at: 0001-01-01T00:00:00Z



INFO:app.utils.converters:records: ({'props': {'person_id': 'P-500'}, 'labels': ['Person']}, {'props': {'account_id': 'ACC-4'}, 'labels': ['Account']}, {'props': {}, 'rel_type': 'HAS'})
INFO:app.utils.converters:function => to_model_datagraph()
INFO:app.utils.converters:records: ({'props': {'person_id': 'P-500'}, 'labels': ['Person']}, {'props': {'account_id': 'ACC-500'}, 'labels': ['Account']}, {'props': {}, 'rel_type': 'HAS'})

