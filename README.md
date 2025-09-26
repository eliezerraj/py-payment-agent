# py-payment-agent
py-payment-agent

# create venv
python3 -m venv .venv

# activate
source .venv/bin/activate

# install requirements
pip install -r requirements.txt

# run
python3 agent.py


// Untitled favorite
//MATCH (n) DETACH DELETE n;

//CREATE(:Person {name: 'eliezer'})
//CREATE(:Person {name: 'juliana'})
//CREATE(:Account {account_id: 'acc-001'})
//CREATE(:Account {account_id: 'acc-002'})
//CREATE(:Account {account_id: 'acc-003'})
//CREATE(:Account {account_id: 'acc-004'})
MATCH(person: Person {name: 'eliezer'})
MATCH(account: Account {account_id: 'acc-001'})
MERGE(person)-[:HAS]->(account)
MATCH (n) DETACH DELETE n;