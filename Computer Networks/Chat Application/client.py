import socket
from threading import Lock,Thread
import gc
from cryptography.hazmat.primitives.asymmetric import rsa,padding
from cryptography.hazmat.primitives import serialization,hashes
from cryptography.hazmat.backends import default_backend
import sys
import base64
import hashlib
from numpy.random import randint
import time

publicKey = []
privateKey = []
publicKeyCopy = []

mode = int(sys.argv[3])

def generateKeyPair():
	global publicKey
	global privateKey
	global publicKeyCopy
	privateKey = rsa.generate_private_key(public_exponent=2*randint(low=4,high=10000)+1,key_size=512,backend=default_backend())
	publicKey = privateKey.public_key()
	privateKey = privateKey.private_bytes(encoding=serialization.Encoding.PEM,format=serialization.PrivateFormat.PKCS8,encryption_algorithm=serialization.NoEncryption())
	publicKey = publicKey.public_bytes(encoding=serialization.Encoding.DER,format=serialization.PublicFormat.SubjectPublicKeyInfo)
	publicKeyCopy = str(base64.b64encode(publicKey).decode("utf-8"))

def encrypt(message,key):
	key = base64.b64decode(key.encode("utf-8"))
	key = serialization.load_der_public_key(key,backend=default_backend())
	encrypted = key.encrypt(message,padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA1()),algorithm=hashes.SHA1(),label=None))
	return encrypted

def decrypt(encrypted,key):
	key = serialization.load_pem_private_key(key,password=None,backend=default_backend())
	original_message = key.decrypt(encrypted,padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA1()),algorithm=hashes.SHA1(),label=None))
	return original_message

def getHashDigest(message):
	message = hashlib.sha256(message.encode("utf-8"))
	return message.hexdigest()

def sign(message):
	key = serialization.load_pem_private_key(privateKey,password=None,backend=default_backend())
	encrypted = key.sign(message,padding.PSS(mgf=padding.MGF1(hashes.SHA1()),salt_length=padding.PSS.MAX_LENGTH),hashes.SHA1())
	return encrypted

def verifySignature(signature,message,key):
	key = base64.b64decode(key.encode("utf-8"))
	key = serialization.load_der_public_key(key,backend=default_backend())
	try:
		key.verify(signature,message,padding.PSS(mgf=padding.MGF1(hashes.SHA1()),salt_length=padding.PSS.MAX_LENGTH),hashes.SHA1())
		return True
	except:
		return False
	
if mode > 0:
	generateKeyPair()

port = int(sys.argv[2]) # The port used by the server
buffer_size = 1024

username = input("Enter username ")
host = str(sys.argv[1])

lock = Lock()

registered = False

errorMessages = {"MALFORMED":"ERROR 100 Malformed username\n\n","NOREGISTRATION":"ERROR 101 No user registered\n\n","CANTSEND":
"ERROR 102 Unable to send\n\n","HEADERINCOMPLETE":"ERROR 103 Header incomplete\n\n","DUPLICATEUSER":"ERROR 104 Username already registered\n\n","USERNOTFOUND":"ERROR 110 User not registered\n\n","NOMATCH":"Error 111 Sender and Receiver username not matching \n\n","SHUTDOWN":"ERROR 000 UNREGISTER\n\n"}

displayMessages = {'TAMPERED':"Following message is tampered\n",'HEADERINCOMPLETE':"Incomplete header\n",'USERNOTFOUND':"No such username","ERRORSENDING":"Error in sending message\n","MALFORMED":"Malformed username,enter new username\n","USERNAMETAKEN":"Username Taken,enter new username\n","ENTER":"Enter message \n","INCORRECT":"Incorrect format, type again\n","SENT":"Message sent","SHUTDOWN":"Closing connection"}

class Log(list):
	def append(self,message):
		list.append(self,message)

log = Log()

sending_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
receiving_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

sending_socket.connect((host,port))
receiving_socket.connect((host,port))

class SendingThread(Thread):
	def __init__(self,conn):
		Thread.__init__(self)
		self.conn = conn
		self.type = "SEND"
		self.userName = username

	def register(self):
		while True:
			if mode == 0:
				message = "REGISTER TOSEND " + self.userName + "\n\n"
			else:
				message = "REGISTER TOSEND " + self.userName + "\nKey : "+publicKeyCopy+"\n\n"
			self.sendMessage(message)
			data = self.streamHeader()
			errorFound = self.analyzeForErrors(data,0)
			if errorFound == 0:
				break
		global registered
		registered = True
		return

	def analyzeForErrors(self,data,flag):
		if flag == 0:
			response = data[0].split()
			if response[0] == "REGISTERED":
				return 0
			if response[1] == "100":
				self.askForNewUserName(displayMessages['MALFORMED'])
				return 1
			if response[1] == "104":
				self.askForNewUserName(displayMessages['USERNAMETAKEN'])
				return 1
			else:
				print(data[0])
				return 1
		else:
			response = data[0].split()
			if response[0] == "SENT":
				return 0
			elif response[1] == "102":
				print(displayMessages['ERRORSENDING'])
				return 1
			elif response[1] == "103":
				print(displayMessages['HEADERINCOMPLETE'])
				return 1
			elif response[1] == "000":
				return -1
			else:
				return 1

	def sendMessage(self,message):
		self.conn.sendall(b''+str.encode(message))

	def askForNewUserName(self,text):
		global username
		username = input(text)
		self.userName = username

	def streamHeader(self):
		data = []
		curr = ""
		while True:
			packet = self.conn.recv(1)
			if not packet:
				break
			curr = curr + str(packet.decode("utf-8"))
			if curr == "\n":
				return data
			elif curr[-1] == "\n":
				data.append(curr[:-1])
				curr = ""

	def run(self):
		self.register()
		exit = 0
		while exit!=-1:
			message = input(displayMessages['ENTER'])
			message = message.split(" ",2)
			if message[0] != "@":
				print(displayMessages['INCORRECT'])
				continue
			exit = self.chatWithPerson(message[1],message[2])
		print(displayMessages['SHUTDOWN'])

	def streamMessage(self,n):
		message = ""
		while len(message)<n:
			packet = self.conn.recv(n-len(message))
			if not packet:
				break
			message = message + str(packet.decode("utf-8"))
		return message

	def chatWithPerson(self,username,message):
		if mode == 0:
			data = "SEND "+username+"\n\n"
		if mode == 1 or mode == 2:
			key = self.fetchKey(username)
			if key == None:
				return
			message = str(base64.b64encode(encrypt(str.encode(message,"utf-8"),key)).decode("utf-8"))
			length = len(message)
			if mode == 2:
				digest = getHashDigest(message)
				digest = sign(digest.encode('utf-8'))
				digest = str(base64.b64encode(digest).decode('utf-8'))
				data = "SEND "+username+"\nContent-length : "+str(length)+"\nHash : "+digest+"\n\n"
			else:
				data = "SEND "+username+"\nContent-length : "+str(length)+"\n\n"
		self.sendMessage(data)
		log.append("Sent header to server")
		self.sendMessage(message)
		data = self.streamHeader()
		log.append("Got confirmation from server")
		errorFound = self.analyzeForErrors(data,1)
		if errorFound == 0:
			print("Message sent")
		return errorFound

	def fetchKey(self,username):
		message = "FETCHKEY "+username+"\n\n"
		self.sendMessage(message)
		response = self.streamHeader()
		if response[0].split()[1] == "110":
			print(displayMessages['USERNOTFOUND'])
			return
		length = int(response[0].split()[1])
		key = self.streamMessage(length)
		return key

class ReceivingThread(Thread):
	def __init__(self,conn):
		Thread.__init__(self)
		self.conn = conn
		self.type = "RECV"
		self.userName = username

	def register(self):
		if mode == 0:
			message = "REGISTER TORECV " + self.userName + "\n\n"
		else:
			message = "REGISTER TORECV " + self.userName + "\nKey : "+publicKeyCopy+"\n\n"
		self.sendMessage(message)
		data = self.streamHeader()
		return	

	def sendMessage(self,message):
		try:
			self.conn.sendall(b''+str.encode(message))
		except:
			print("Couldnt send data")

	def streamHeader(self):
		data = []
		curr = ""
		while True:
			packet = self.conn.recv(1)
			if not packet:
				break
			curr = curr + str(packet.decode("utf-8"))
			if curr == "\n":
				return data
			elif curr[-1] == "\n":
				data.append(curr[:-1])
				curr = ""

	def askForNewUserName(self,text):
		global username
		username = input(text)
		self.userName = username

	def streamMessage(self,n):
		message = ""
		while len(message)<n:
			packet = self.conn.recv(n-len(message))
			if not packet:
				break
			message = message + str(packet.decode("utf-8"))
		return message

	def analyzeForErrors(self,header,flag):
		if header[0][:-2] == errorMessages['SHUTDOWN']:
			return -1
		data = header[0].split()
		if len(header)<2+int(mode>1):
			for e in header:
				data = e.split()
				index = e.find('Content-length')
				if index != -1:
					self.streamMessage(int(e.split(':')[1][1:]))
					self.sendMessage(errorMessages['HEADERINCOMPLETE'])
					return 1
			self.sendMessage(errorMessages['SHUTDOWN'])
			return -1
		return 0

	def receiveAndConfirmMessage(self):
		data = self.streamHeader()
		errorFound = self.analyzeForErrors(data,1)
		if errorFound != 0:
			return errorFound
		forward,sender = data[0].split()
		_,length = data[1].split(":")
		length = int(length[1:])
		if mode == 2:
			digest = data[2].split(":")[1][1:]
			digest = base64.b64decode(digest.encode('utf-8'))
			key = data[3].split(":")[1][1:]
		message = self.streamMessage(length)
		log.append("Got message from server")
		if mode != 0:
			if mode == 2:
				actualDigest = getHashDigest(message).encode('utf-8')
				if verifySignature(digest,actualDigest,key) == False:
					print(errorMessages['TAMPERED'])
			message = str(decrypt(base64.b64decode(message.encode("utf-8")),privateKey).decode("utf-8"))
		self.sendMessage("RECEIVED "+sender+"\n\n")
		log.append("Sent confirmation to server")
		print("# "+sender + " : "+message)
		return 1

	def run(self):
		self.register()
		exit = 1
		while exit!=-1:
			exit = self.receiveAndConfirmMessage()
		print(displayMessages['SHUTDOWN'])

sendingThread = SendingThread(sending_socket)
sendingThread.start()
while registered == False:
	continue

receivingThread = ReceivingThread(receiving_socket)
receivingThread.start()

sendingThread.join()
receivingThread.join()

sending_socket.close()
receiving_socket.close()

