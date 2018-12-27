import json
import socket
import dns.resolver
from tinydb import TinyDB, Query
import time

cacheDB = TinyDB('DNSCacheDB.json')

mySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
mySocket.bind(('0.0.0.0', 7777))
mySocket.listen(1)

while True:
    socketObject, addressInfo = mySocket.accept()
    byteData = socketObject.recv(1024)
    data = json.loads(str(byteData, encoding='utf_8'))
    query = Query()
    queryAnswer = cacheDB.search((query.type == data['type']) & (query.target == data['target']))
    cacheAnswered = False

    if queryAnswer:
        queryTuple = queryAnswer[0]
        if int(time.time()) - queryTuple['responseTime'] < queryTuple['ttl']:
            print('request was cached!')
            socketObject.send(bytes(json.dumps(queryTuple['response']) + " authority: " + json.dumps(queryTuple['authority']), encoding='utf_8'))
            socketObject.close()
            cacheAnswered = True
        else:
            print('request was cached but its ttl has been over!')
            cacheDB.remove((query.type == data['type']) & (query.target == data['target']))

    if not cacheAnswered:
        print('DNS query to server ...')
        dnsAnswer = None
        response = []
        try:
            myResolver = dns.resolver.Resolver()
            myResolver.nameservers = [data['server']]
            dnsAnswer = myResolver.query(data['target'], data['type'])
            print('DNS answer receved')
            authorative = bin(dnsAnswer.response.flags)[7]
            response = [str(x) for x in dnsAnswer]
        except dns.exception.Timeout as e:
            print(e.args)
            socketObject.send(bytes(e.args[0], encoding='utf_8'))
            continue
        except Exception as e:
            print(e.args, 'cherto pert')
            socketObject.send(bytes(e.args[0], encoding='utf_8'))
            continue
        cacheDB.insert({
            'type': data['type'],
            'target': data['target'],
            'ttl': dnsAnswer.ttl,
            'responseTime': int(time.time()),
            'response': response,
            'authority': '0',
        })
        socketObject.send(bytes(json.dumps(response) + " authority: " + authorative, encoding='utf_8'))
        socketObject.close()
