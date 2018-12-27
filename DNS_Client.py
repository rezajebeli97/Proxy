import json
import socket



request = input()
req_type , req_server, req_target = request.split()

query = {
    'type': req_type,
    'server': req_server,
    'target': req_target,
}

mySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
mySocket.settimeout(10)

mySocket.connect(('127.0.0.1', 7777))

while True:
    try:
        mySocket.send(bytes(json.dumps(query), encoding='utf_8'))
        response = mySocket.recv(1024)
        break
    except Exception as e:
        print('resend')


print(str(response, encoding='utf_8'))

mySocket.close()


