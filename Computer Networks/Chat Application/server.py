import socket
from threading import Lock,Thread
import gc
from cryptography.hazmat.primitives.asymmetric import rsa,padding
from cryptography.hazmat.primitives import serialization,hashes
from cryptography.hazmat.backends import default_backend
import base64
from numpy.random import randint
import sys

privateKey = []
publicKey = []
publicKeyCopy = []

def generateKeyPair():
	global publicKey
	global privateKey
	global publicKeyCopy
	privateKey = rsa.generate_private_key(public_exponent=2*randint(low=4,high=10000)+1,key_size=512,backend=default_backend())
	publicKey = privateKey.public_key()
	privateKey = privateKey.private_bytes(encoding=serialization.Encoding.PEM,format=serialization.PrivateFormat.PKCS8,encryption_algorithm=serialization.NoEncryption())
	publicKey = publicKey.public_bytes(encoding=serialization.Encoding.DER,format=serialization.PublicFormat.SubjectPublicKeyInfo)
	publicKeyCopy = str(base64.b64encode(publicKey).decode("utf-8"))

def decrypt(encrypted,key):
	key = serialization.load_pem_private_key(key,password=None,backend=default_backend())
	original_message = key.decrypt(encrypted,padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA1()),algorithm=hashes.SHA1(),label=None))
	return original_message

host = str(sys.argv[1])
port = int(sys.argv[2])
buffer_size = 1024
mode = int(sys.argv[3]) # 0 - Unencrypted, 1- Encrypted, 2- Encrypted with signatures

maxHosts = int(sys.argv[4])

if mode>0:
	generateKeyPair()

lock = Lock()

errorMessages = {"MALFORMED":"ERROR 100 Malformed username\n\n","NOREGISTRATION":"ERROR 101 No user registered\n\n","CANTSEND":
"ERROR 102 Unable to send\n\n","HEADERINCOMPLETE":"ERROR 103 Header incomplete\n\n","DUPLICATEUSER":"ERROR 104 Username already registered\n\n","USERNOTFOUND":"ERROR 110 User not registered\n\n","NOMATCH":"Error 111 Sender and Receiver username not matching \n\n","NOKEY":"Error 112 No key sent\n\n",'SHUTDOWN':"ERROR 000 UNREGISTER\n\n"}

class Log(list):
	def append(self,message):
		list.append(self,message)
		if len(self)>10:
			self = Log()

log = Log()

sending_usernames = {} # Dict from (username) to (addr,port)
receiving_usernames = {}
sockets = {} # Dict from (addr,port) to sockets
threads = []
public_keys = {}
registered = {}

receiving_usernames['HOST'] = (host,port)
if mode!=0:
	public_keys['HOST'] = publicKeyCopy

class ClientThread(Thread):
	def __init__(self,ip,port,conn):
		Thread.__init__(self)
		self.ip = ip 
		self.port = port
		self.conn = conn
		self.type = ""
		self.username = ""

	def streamHeader(self,conn):
		data = []
		curr = ""
		while True:
			packet = conn.recv(1)
			if not packet:
				break
			curr = curr + str(packet.decode("utf-8"))
			if curr == "\n":
				return data
			elif curr[-1] == "\n":
				data.append(curr[:-1])
				curr = ""
	
	def streamMessage(self,n,conn):
		message = ""
		while len(message)<n:
			packet = conn.recv(n-len(message))
			if not packet:
				break
			message = message + str(packet.decode("utf-8"))
		return message

	def sendMessage(self,message,conn):
		conn.sendall(b''+str.encode(message))

	def analyzeForErrors(self,header,flag):
		if flag == 0: # Before registration errors
			data = header[0].split()
			if data[0]!="REGISTER": # If something different
				self.sendMessage(errorMessages["NOREGISTRATION"],self.conn)
				return 1
			if data[2].isalnum() == False: # Malformed username
				self.sendMessage(errorMessages["MALFORMED"],self.conn)
				return 1
			if data[1][2:] == "SEND":
				if data[2] in sending_usernames.keys(): # If username already found
					self.sendMessage(errorMessages['DUPLICATEUSER'],self.conn) # Choose another username
					return 1
			else:
				if data[2] in receiving_usernames.keys(): # If username already found
					self.sendMessage(errorMessages['NOMATCH'],self.conn) # Choose another username
					return 1
			if mode!=0:
				if len(header)<2 or header[1].split(':')[0]!="Key ":
					self.sendMessage(errorMessages['NOKEY'],self.conn)
					return 1
			return 0
		elif flag == 1:
			if header[0].split()[0] == "FETCHKEY":
				return 0
			if len(header)<2+int(mode>1):
				for e in header:
					print(e)
					data = e.split()
					index = e.find('Content-length')
					if index != -1:
						self.streamMessage(int(e.split(':')[1][1:]),self.conn)
						self.sendMessage(errorMessages['HEADERINCOMPLETE'],self.conn)
						return 1
				return -1
			return 0
		else:
			data = header[0].split()
			if data[1] == "102":
				self.sendMessage(errorMessages['CANTSEND'],self.conn)
				return 1
			if data[1] == "103":
				self.sendMessage(errorMessages['CANTSEND'],self.conn)
				return 1
			if data[1] == "000":
				return -1
			return 0

	def registerClient(self):
		while True:
			header = self.streamHeader(self.conn)
			lock.acquire()
			errorFound = self.analyzeForErrors(header,0)
			if errorFound == 0:
				data = header[0].split()
				if data[1][2:] == "SEND":
					sending_usernames[data[2]] = (self.ip,self.port)
					registered[data[2]] = False
				else:
					receiving_usernames[data[2]] = (self.ip,self.port)
					registered[data[2]] = True
				self.sendMessage("REGISTERED "+data[1]+" "+data[2]+"\n\n",self.conn)
				self.username = data[2]
				self.type = data[1][2:]
				if mode != 0:
					public_keys[self.username] = header[1].split(':')[1][1:]
				lock.release()
				break
			lock.release()
		return

	def listenForMessages(self):
		header = self.streamHeader(self.conn)
		log.append("Got header from sender")
		errorFound = self.analyzeForErrors(header,1)
		if errorFound != 0:
			return errorFound
		data = header[0].split()
		if data[0] == "SEND":
			receiver = data[1]
			messageLength = int(header[1].split(':')[1][1:])
			message = self.streamMessage(messageLength,self.conn)
			log.append("Got message from sender")
			args = {}
			args['receiver'],args['message'], = receiver,message
			if mode == 2:
				digest = header[2].split(':')[1][1:]
				args['digest'] = digest
			return args
		if data[0] == "FETCHKEY":
			args = {}
			args['key'] = data[1]
			return args

	
	def forwardMessage(self,args):
		receiver = args['receiver']
		message = args['message']
		if receiver not in receiving_usernames.keys():
			self.sendMessage(errorMessages['USERNOTFOUND'],self.conn)
			return
		if mode == 0 or mode == 1:
			data = "FORWARD "+ self.username+"\nContent-length : "+str(len(message))+"\n\n"
		if mode == 2:
			key = public_keys[self.username]
			data = "FORWARD "+ self.username+"\nContent-length : "+str(len(message))+"\nHash : "+args['digest']+"\nKey : "+key+"\n\n"
		self.sendMessage(data,sockets[receiving_usernames[receiver]])
		log.append("Sent header to receiver")
		self.sendMessage(message,sockets[receiving_usernames[receiver]])
		log.append("Sent message to receiver")
		data = self.streamHeader(sockets[receiving_usernames[receiver]])
		errorFound = self.analyzeForErrors(data,2)
		if errorFound != 0:
			return errorFound
		log.append("Got confirmation by receiver")
		data = data[0].split()
		if data[0] == "RECEIVED" and data[1] == self.username:
			self.sendMessage("SENT "+receiver+"\n\n",self.conn)
		log.append("Sent confirmation to sender")
		return

	def processMessageToServer(self,args):
		if mode == 0:
			if args['message'] == "UNREGISTER":
				return -1
		else:
			message = str(decrypt(base64.b64decode(args['message'].encode("utf-8")),privateKey).decode("utf-8"))
			if message == "UNREGISTER":
				return -1
		return 1

	def run(self):
		self.registerClient()
		if self.type == "RECV":
			return
		exit = 1
		while exit!=-1:
			args = self.listenForMessages()
			if type(args) == int:
				exit = args
				continue
			if "receiver" in args.keys():
				if args['receiver'] == 'HOST':
					exit = self.processMessageToServer(args)
				else:
					exit = self.forwardMessage(args)
			if "key" in args.keys():
				if args['key'] in public_keys.keys():
					key = public_keys[args["key"]]
					length = len(key)
					self.sendMessage("Key-Length "+str(length)+"\n\n",self.conn)
					self.sendMessage(key,self.conn)
				else:
					self.sendMessage(errorMessages['USERNOTFOUND'],self.conn)
		self.sendMessage(errorMessages['SHUTDOWN'],self.conn)
		self.sendMessage(errorMessages['SHUTDOWN'],sockets[receiving_usernames[self.username]])
		del sockets[receiving_usernames[self.username]]
		del sockets[sending_usernames[self.username]]
		del sending_usernames[self.username]
		del receiving_usernames[self.username]
		del registered[self.username]
		if mode!=0:
			del public_keys[self.username]

with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
	s.bind((host,port))
	s.listen()
	for i in range(2*maxHosts):
		conn,addr = s.accept()
		thread = ClientThread(addr[0],addr[1],conn)
		sockets[addr] = conn
		threads.append(thread)
		thread.start()

for t in threads:
	t.join()