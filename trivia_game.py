import os
import random
import json
import datetime
import string
import logging
import os.path
import json


from Crypto.PublicKey import RSA

log = logging.getLogger(__name__)
def cleanstr(s, n=20):
    "clean string to printable chars with max length n"

    if s == None:
        return "NONE"

    try:
        s = s.decode()
    except AttributeError:
        pass

    try:
        q = ''.join(x for x in s[:n] if x in string.printable[:64])

    except TypeError:
        q = "TypeError"

    return q

class TriviaClient:
    def __init__(self, client_socket, client_dir='./user_dat'):
        self.skt = client_socket
        self.connect_at = datetime.datetime.now()
        self.current_q = None
        self.question_sent = None
        self.handle = self.authenticate
        self.score = 0
        self.counters = [0,0,0,0] # auth, correct, incorrect, invalid
        self.username = None
        self.client_dir = client_dir
        self.authenticated = False
        log.info("New client {}".format(self.skt.getpeername()))
    def authenticate(self, msg):
        "the default handler until authenticated"
        msg = msg.decode()
        self.username = cleanstr(msg.strip())[5:]
        log.info("Auth from {}".format(self.username))

        #send nonce
        self.nonce = "{}".format(random.random())
        self.skt.send(self.nonce.encode())

        self.handle = self.authenticate_response
    def authenticate_response(self, msg):
        pubkey = os.path.join(
            os.path.expanduser('~'+self.username),
            "id_rsa.pub")

        if os.path.exists(pubkey):
            try:
                with open(pubkey, 'r') as f:
                    rsa = RSA.importKey(f.read())
                    # log.info("got key {}".format(rsa))
                    # log.info("encrypt {}".format(rsa.can_encrypt()))
                    # log.info("has_private {}".format(rsa.has_private()))

                    try:
                        resp = rsa.encrypt(msg, 32)[0].decode()
                    except Exception as x:
                        log.error(x)
                        resp = None

                    # log.info("auth resp {}, wanted {}".format(resp, self.nonce))
                    if resp == self.nonce:
                        self.authenticated = True
                        self.skt.send(b"AUTHORIZED")
                        self.restore()

                        self.counters[0] += 1
                        # authenticated, set game handler
                        self.handle = self.play
                    else:
                        self.skt.send(b"NOTAUTHORIZED")
                        self.handle = self.authenticate
            except PermissionError:
                self.skt.send("NOPERMS {}".format(pubkey).encode())
                self.handle = self.authenticate
        else:
            self.skt.send("NOKEY {}".format(pubkey).encode())

            self.handle = self.authenticate
    def save(self):
        "write score history for this player"
        filename = os.path.join(self.client_dir, self.username)
        with open(filename, 'w') as f:
            json.dump({
                'score': self.score,
                'counters': self.counters
            }, f)
    def restore(self):
        filename = os.path.join(self.client_dir, self.username)
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                h = json.load(f)
                self.score = h['score']
                self.counters = h['counters']

    def play(self, msg):
        "when a msg is recieved on this game"
        msg = msg.decode()
        log.info("{} play: {}".format(self.skt.getpeername(), msg))

        if self.current_q:
            resp_time = datetime.datetime.now() - self.question_sent
            if msg in self.current_q['choices']:
                r = ""
                if msg == self.current_q['answer']:
                    self.score += max(60, 100 - resp_time.total_seconds())
                    r = "CORRECT SCORE {}".format(int(self.score))
                    self.counters[1] += 1
                else:
                    self.score -= (100 / len(self.current_q['choices']))
                    r = "INCORRECT SCORE {}".format(int(self.score))
                    self.counters[2] += 1
                self.skt.send(r.encode())
                self.save()
            else:
                self.counters[3] += 1
                self.skt.send(b"INVALID")

            # invalidate the question
            self.current_q = None
        else:
            self.skt.send(b"NOQUESTION")

    def send_question(self, question):
        if self.authenticated:
            self.current_q = question
            log.info("{} -> SendQ: {}".format(
                self.skt.getpeername(),
                question['question']))

            msg = [question['question']] + question['choices']
            self.skt.send('\n'.join(msg).encode())
            self.question_sent = datetime.datetime.now()


""" question format is a dict:
{
'question': 'A “face mask” is a common penalty in what sport?',

'choices': ['FOOTBALL', 'ILLEGAL', 'PLAYER', 'MASK', 'FACE', 'HELMET'],

'answer': 'FOOTBALL',

'created': '2019-04-24T21:21:57.664294'}

"""
class TriviaServer:
    def __init__(self, trivia_dir='./trivia'):
        self.questions = list(
            map(lambda x: os.path.join(trivia_dir, x),
                os.listdir(trivia_dir))
            )

    def get_question(self):
        qf = random.choice(self.questions)
        with open(qf, 'r') as f:
            return json.load(f)


if __name__ == "__main__":
    ts = TriviaServer()

    print ("have {} questions".format(len(ts.questions)))
    for i in range(10):
        print ("\t{}".format(ts.get_question()))
