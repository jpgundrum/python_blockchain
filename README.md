# Blockchain in Python
This is a project I did for a blockchain course I took during college. It assumes a consortium setting where everyone is aware of the others participating, with reputation based nodes, and nodes act that cautiously (Don't have to fight for block proposal and suspicious of block proposal).
The peer-to-peer system can use 3+ blockchain nodes to form a consensus.

## Start the blockchain
To start a 3 node blockchain you can run the cmds:

```
python3 server.py -p 5001 -n 5001 5002 5003
python3 server.py -p 5002 -n 5001 5002 5003
python3 server.py -p 5003 -n 5001 5002 5003
```

## Generate the genesis block
In a 4th terminal execute the cmd below to create the genesis block, which will kick-start the rest of the blockchain execution.

```curl http://localhost:5001/startexp/```


## Send transactions to the nodes
The following cmds execute transactions that result in a global change of state. Sender A is initialized to 10000 tokens on startup

1. Send 5000 tokens from A to B

    ```curl -X POST http://localhost:5001/transactions/new -H 'Content-Type: application/json' -d '{"sender": "A", "recipient": "B", "amount": 5000}'```
2. Send 1500 tokens from B to C


    ```curl -X POST http://localhost:5001/transactions/new -H 'Content-Type: application/json' -d '{"sender": "B", "recipient": "C", "amount": 1500}'```
3. Sender 100 tokens from C to A

    ```curl -X POST http://localhost:5001/transactions/new -H 'Content-Type: application/json' -d '{"sender": "C", "recipient": "A", "amount": 100}'```

### Analyzing the data
When all 3 transactions take place the following history data should be reported on all nodes: 
```{'A': [[1, 10000], [4, -5000], [16, 100]], 'B': [[4, 5000], [10, -1500]], 'C': [[10, 1500], [16, -100]]}```

The letter in each key-value pair represents a node, and the list of lists inside each node represents transaction history [block number, transaction amount]. You may have different block numbers and that it ok. For example A was initialized to 10000 tokens. The first transaction removed 5000 tokens from A and moved them over to B during the mining of the 4th block. A displays the subtraction of values **([4, -5000])** and B contains the new funds added to the node with **[4, 5000]**. The same logic follows when B sends to C and C sends back to A

### Debugging tools
To get the in-state memory of each node use cmd: `curl http://localhost:5001/dump`

To control time node waits before committing a block add `-t 10` when you run a cmd. In this case each node will wait 10 seconds before it proposes a block.

There are other logging ares used throughout the file that can be umcommented to get more in-depth analysis.