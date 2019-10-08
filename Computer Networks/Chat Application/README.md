# ChatApplication

### Made as a part of the course COL334 (Computer Networks) at IIT Delhi

A minimal client-server chat application using socket programming in Python supporting encryption and signatures

### Instructions

Run server.py as -
>python3 server.py ip_address port mode maxClients

Run client.py as-
>python3 client.py server_ip_address server_port mode

#### Mode 0 = Unencrypted messages
#### Mode 1 = Encrypted (Uses RSA asymmetric key encryption)
#### Mode 2 = Encrypted with signatures (Hash digests of the message signed by the private key of the sender sent along the message)

MaxClients is the maximum number of hosts that connect to the server.

Ip address and port of the server are the ones we wish the server to bind to.

#### Type your messages as "@ username message"

#### For sending the unregister/quit message type "@ HOST UNREGISTER"
