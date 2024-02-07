# forked from https://github.com/dvf/blockchain

import hashlib
import json
import time
import threading
import logging
import copy

import requests
from flask import Flask, request

class Transaction(object):
    def __init__(self, sender, recipient, amount):
        self.sender = sender # constraint: should exist in state
        self.recipient = recipient # constraint: need not exist in state. Should exist in state if transaction is applied.
        self.amount = amount # constraint: sender should have enough balance to send this amount

    def __str__(self) -> str:
        return "T(%s -> %s: %s)" % (self.sender, self.recipient, self.amount)

    def encode(self) -> str:
        return self.__dict__.copy()

    @staticmethod
    def decode(data):
        return Transaction(data['sender'], data['recipient'], data['amount'])

    def __lt__(self, other):
        if self.sender < other.sender: return True
        if self.sender > other.sender: return False
        if self.recipient < other.recipient: return True
        if self.recipient > other.recipient: return False
        if self.amount < other.amount: return True
        return False
    
    def __eq__(self, other) -> bool:
        return self.sender == other.sender and self.recipient == other.recipient and self.amount == other.amount

class Block(object):
    def __init__(self, number, transactions, previous_hash, miner):
       # print("Created block with txns:", len(transactions))
        self.number = number # constraint: should be 1 larger than the previous block
        self.transactions = transactions # constraint: list of transactions. Ordering matters. They will be applied sequentlally.
        self.previous_hash = previous_hash # constraint: Should match the previous mined block's hash
        self.miner = miner # constraint: The node_identifier of the miner who mined this block
        self.hash = self._hash()

    def _hash(self):
        return hashlib.sha256(
            str(self.number).encode('utf-8') +
            str([str(txn) for txn in self.transactions]).encode('utf-8') +
            str(self.previous_hash).encode('utf-8') +
            str(self.miner).encode('utf-8')
        ).hexdigest()

    def __str__(self) -> str:
        return "B(#%s, %s, %s, %s, %s)" % (self.hash[:5], self.number, self.transactions, self.previous_hash, self.miner)
    
    def encode(self):
        encoded = self.__dict__.copy()
        encoded['transactions'] = [t.encode() for t in self.transactions]
        return encoded
    
    @staticmethod
    def decode(data):
        txns = [Transaction.decode(t) for t in data['transactions']]
        return Block(data['number'], txns, data['previous_hash'], data['miner'])

class State(object):
    def __init__(self):
        # TODO: You might want to think how you will store balance per person.
        # You don't need to worry about persisting to disk. Storing in memory is fine.
        self.balances = {}
        self.history_list = {}
        pass
        

    def encode(self):
        return self.balances

    def validate_txns(self, txns):
        result = []
        # You receive a list of transactions, and you try applying them to the state.
        # If a transaction can be applied, add it to result. (should be included)

        temp_state = copy.deepcopy(self.balances)
        for tx in txns:
            if tx.sender in temp_state:
                if temp_state[tx.sender] >= tx.amount:
                    if tx.recipient not in temp_state:
                        temp_state[tx.recipient] = 0

                    temp_state[tx.sender] -= tx.amount
                    temp_state[tx.recipient] += tx.amount
                    result.append(tx)
        
        return result

    def apply_block(self, block):
    #    logging.info("Block (#%s) applied to state. %d transactions applied" % (block.hash, len(block.transactions)))

        found_sender = False
        found_recipient = False

        for trans in block.transactions:
            if trans.recipient not in self.balances:
                self.balances[trans.recipient] = 0

            self.balances[trans.sender] -= trans.amount
            self.balances[trans.recipient] += trans.amount

            if trans.sender not in self.history_list:
                self.history_list[trans.sender] = []
            if trans.recipient not in self.history_list:
                self.history_list[trans.recipient] = []

            #update sender in history list
            self.history_list[trans.sender].append([block.number, int(trans.amount) * -1])
            
            #update recipient in history list
            self.history_list[trans.recipient].append([block.number, trans.amount])

        print(self.history_list)




    def history(self, account):

        dict_history = {}
        dict_list = []

        if account in self.history_list:
            for number, amount in self.history_list[account]:
                if number not in dict_history:
                    dict_history[number] = 0
                dict_history[number] += amount
            for key, value in dict_history.items():
                dict_list.append([key, value])
            return dict_list
        
        return []


class Blockchain(object):
    def __init__(self):
        self.nodes = []
        self.node_identifier = 0
        self.block_mine_time = 5
        self.iteration = 0

        # in memory datastructures.
        self.current_transactions = [] # A list of `Transaction`
        self.chain = [] # A list of `Block`
        self.state = State()

    def is_new_block_valid(self, block, received_blockhash):
        """
        Determine if I should accept a new block.
        Does it pass all semantic checks? Search for "constraint" in this file.
        :param block: A new proposed block
        :return: True if valid, False if not
        """

        # 1. Hash should match content X
        # 2. Previous hash should match previous block X
        # 3. Transactions should be valid (all apply to block)
        # 4. Block number should be one higher than previous block
        # 5. miner should be correct (next RR)


        if block.hash != received_blockhash or block.miner != self.nodes[self.iteration % len(self.nodes)]:
            print("is_new_block_valid: failed at check 1")
            return False 

        if len(self.chain) == 0 and block.previous_hash == "0xfeedcafe":
            if block.number != 1:
                print("is_new_block_valid: failed at check 2")
                return False
            return True
        
        if block.previous_hash != self.chain[-1].hash or block.number != self.chain[-1].number + 1:
            print("is_new_block_valid: failed at check 3")
            return False

        #check its transactions
        temp_state = copy.deepcopy(self.state.balances)
        for tx in block.transactions:
            if tx.recipient not in temp_state:
                temp_state[tx.recipient] = 0
            if tx.sender not in temp_state:
                print("is_new_block_valid: failed at check 4")
                return False

            if temp_state[tx.sender] >= tx.amount:
                temp_state[tx.sender] -= tx.amount
                temp_state[tx.recipient] += tx.amount
            else:
                print("is_new_block_valid: failed at check 5")
                return False
        
        return True

    def trigger_new_block_mine(self, genesis=False):
        thread = threading.Thread(target=self.__mine_new_block_in_thread, args=(genesis,))
        thread.start()

    def __mine_new_block_in_thread(self, genesis=False):
        """
        Create a new Block in the Blockchain
        :return: New Block
        """
    #    logging.info("[MINER] waiting for new transactions before mining new block...")
        time.sleep(self.block_mine_time) # Wait for new transactions to come in
        miner = self.node_identifier

        if genesis:
            block = Block(1, [], '0xfeedcafe', miner)
            self.state.balances["A"] = 10000
            self.state.history_list["A"] = [[1, 10000]]

        else:
           # print("About to create a new block. considering ", len(self.current_transactions), "transactions")
            self.current_transactions.sort()
            valid_txns = self.state.validate_txns(self.current_transactions)
            block = Block(self.chain[-1].number + 1, valid_txns, self.chain[-1].hash, miner)
            
            temp = []
            for tx in self.current_transactions:
                if tx not in valid_txns:
                    temp.append(tx)
            self.current_transactions = temp
        
        self.chain.append(block)
        self.iteration+=1
        self.state.apply_block(block)

       # logging.info("[MINER] constructed new block with %d transactions. Informing others about: #%s" % (len(block.transactions), block.hash[:5]))
        # broadcast the new block to all nodes.
        for node in self.nodes:
            if node == self.node_identifier: continue
            requests.post(f'http://localhost:{node}/inform/block', json=block.encode())
            

    def new_transaction(self, sender, recipient, amount):
        """ Add this transaction to the transaction mempool. We will try
        to include this transaction in the next block until it succeeds.
        """
        self.current_transactions.append(Transaction(sender, recipient, amount))