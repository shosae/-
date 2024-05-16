from flask import Flask, render_template, request, jsonify
import uuid
import hashlib
import datetime
import time

app = Flask(__name__)

# 블록
class Block:
    def __init__(self, index, timestamp, transactions, previous_hash, hash='', nonce=0, difficulty=4):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.hash = hash
        self.nonce = nonce
        self.difficulty = difficulty
    # 해시 계산
    def calculate_hash(self):
        block_info = str(self.index) + str(self.timestamp) + str(self.transactions) + str(self.previous_hash) + str(self.nonce) # 해시에 들어갈 정보
        return hashlib.sha256(block_info.encode()).hexdigest() # 해시값 계산

# 블록체인
class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()] # 제네시스블록 0번째 인덱스로 생성
        self.current_transactions = [] # 거래내역 리스트 생성
        self.difficulty = 4  # 초기 난이도를 4로 설정

    # 제네시스 블록 생성
    def create_genesis_block(self):
        return Block(0, datetime.datetime.now(), [], 'NULL','000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f') #이전 블록 해시는 NULL, 제네시스 블록의 해시값은 비트코인과 동일한 값으로

    # 해시값 추출을 위해 마지막 블록 얻어오기
    def get_latest_block(self):
        return self.chain[-1]

    # 검증된 새로운 블록 추가
    def add_block(self, new_block):
        reward = len(new_block.transactions)  # 거래내역 개수에 따른 보상 계산
        self.add_transaction( # 채굴자에 대한 보상 거래내역
            sender="SERVER",  # 네트워크가
            receiver= "MINER",  # 채굴자에게
            amount = reward*1000 + self.difficulty*500  # 보상 금액 = 거래수*1000 + 난이도*500
        )
        new_block.previous_hash = self.get_latest_block().hash
        self.chain.append(new_block) # 블록체인에 블록 추가
        self.current_transactions = []  # 블록을 추가할 때 현재 거래 내역 리스트 비우기 -> 이미 채굴된 블록 내 거래내역 중 다른 거래 ID로 채굴 xx

    # 작업증명
    def proof_of_work(self, block):
        block.nonce=0 #nonce값 0으로 초기화
        pow_hash = ''
        pow_difficulty = "0" * self.difficulty  # 난이도에 맞는 pow_difficulty 값 생성
        powStartTime = time.time() # 작업증명 시작시간 저장 -> 난이도 계산을 위함
        while not pow_hash.startswith(pow_difficulty): #난이도가 3일때 '000'으로 해시값이 시작하지 않으면
            block.nonce += 1 # nonce를 늘려가며
            pow_hash = block.calculate_hash() # 이전 블록의 정보로 해시값을 계산
        return pow_hash, block.nonce, powStartTime

    # 거래내역 추가
    def add_transaction(self, sender, receiver, amount):
        # 거래 ID 생성
        transaction_id = str(uuid.uuid4())
        # 거래 내용
        transaction = {
            'transaction_id': transaction_id,
            'sender': sender,
            'receiver': receiver,
            'amount': amount
        }
        # 거래내역 리스트에 추가
        self.current_transactions.append(transaction)
        return transaction_id

    # 모든 블록 반환
    def get_all_blocks(self):
        return self.chain

    # 채굴의 난이도 조절
    def adjust_difficulty(self, powStartTime):
            last_block = self.get_latest_block() #마지막 블록
            last_block_time = last_block.timestamp.timestamp()  # 마지막 블록 생성 시간 기록
            powTime = last_block_time - powStartTime # 마지막 블록의 작업증명 시간 = 마지막 블록 생성시간 - 마지막 블록 작업증명 시작시간 / 마지막 블록 생성시간이 더 늦기 때문

            # 작업증명이 걸리는 시간을 5초로 예상
            pow_difficulty_block_time = 5

            # 마지막 블록의 작업증명 시간이 예상 시간의 2배 이상이면 난이도 감소
            if powTime >= pow_difficulty_block_time * 2:
                self.difficulty -= 1

            # 마지막 블록의 작업증명 시간이 예상 시간의 1/2 이하면 난이도 증가
            elif powTime <= pow_difficulty_block_time / 2:
                self.difficulty += 1

            # 난이도가 0보다 작으면 최소값을 1로 설정
            if self.difficulty < 1:
                self.difficulty = 1

            #난이도 반환
            return self.difficulty

# 블록체인 생성
blockchain = Blockchain()

# 거래내역 추가
@app.route('/add_transaction', methods=['POST'])
def add_transaction_route():
    data = request.json
    sender = data.get('sender')
    receiver = data.get('receiver')
    amount = data.get('amount')
    if sender is not None and receiver is not None and amount is not None:
        transaction_id = blockchain.add_transaction(sender, receiver, amount) #거래 id 반환
        response = {"message": "Transaction added successfully", "transaction_id": transaction_id}
        return jsonify(response), 201
    else:
        response = {"error": "Invalid transaction data"}
        return jsonify(response), 400

# 채굴
@app.route('/mine_transaction/<transaction_id>', methods=['GET'])
def mine_transaction(transaction_id):
    current_transactions = blockchain.current_transactions
    # 현재 거래 리스트에서 입력된 거래 찾기
    for transaction in current_transactions:
        if transaction['transaction_id'] == transaction_id:
            # 새로운 블록을 채굴하기 위해 작업증명 수행
            last_block = blockchain.get_latest_block()
            # 작업증명 수행, 이전 블록 넘겨주기
            current_hash, nonce, powStartTime = blockchain.proof_of_work(Block(last_block.index, last_block.timestamp.timestamp(), last_block.transactions,
                                                                               last_block.previous_hash,last_block.hash, last_block.nonce, last_block.difficulty))

            # 새로운 블록 생성
            block = Block(len(blockchain.chain), datetime.datetime.now(), blockchain.current_transactions, last_block.hash, current_hash , nonce, blockchain.difficulty)
            blockchain.add_block(block) # 블록 추가

            # 채굴 난이도 조절
            blockchain.adjust_difficulty(powStartTime)

            response = {
                'message': "New Block Forged",
                'index': block.index,
                'timestamp': block.timestamp,
                'transactions': block.transactions,
                'current_hash': current_hash,
                'previous_hash': block.previous_hash,
                'hash': block.hash,
                'nonce': nonce,
                'difficulty' : blockchain.difficulty
            }
            return jsonify(response), 201
    response = {'error': 'Transaction not found in any block'}
    return jsonify(response), 404

#생성된 블록 거래 ID로 확인
@app.route('/block_by_transaction/<transaction_id>', methods=['GET'])
def get_block_by_transaction(transaction_id):
    for block in blockchain.chain:
        for transaction in block.transactions:
            if transaction['transaction_id'] == transaction_id:
                response = {
                    'block_index': block.index,
                    'block_timestamp': block.timestamp,
                    'block_transactions': block.transactions,
                    'block_previous_hash': block.previous_hash,
                    'block_hash' : block.hash,
                    'nonce' : block.nonce,
                    'difficulty' : block.difficulty
                }
                return jsonify(response), 200
    response = {'error': 'Transaction not found in any block'}
    return jsonify(response), 404


#모든 블록 띄우기
@app.route('/all_blocks')
def get_all_blocks():
    blocks = blockchain.get_all_blocks()
    return render_template('all_blocks.html', blocks=blocks)

#HTML
@app.route('/')
def index():
    return render_template('index.html', blockchain=blockchain.chain)

if __name__ == '__main__':
    app.run(debug=True)
