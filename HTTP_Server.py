import socket
import select
import re
from tinydb import TinyDB, Query
import json
import base64

cacheDB = TinyDB('HTTPCacheDB.json')

def ichecksum(data, sum=0):
    for i in range(0,len(data),2):
        if i + 1 >= len(data):
            sum += ord(data[i]) & 0xFF
        else:
            w = ((ord(data[i]) << 8) & 0xFF00) + (ord(data[i+1]) & 0xFF)
            sum += w
    while (sum >> 16) > 0:
        sum = (sum & 0xFFFF) + (sum >> 16)
    sum = ~sum
    return sum & 0xFFFF

udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.bind(('', 80))
udp_socket.settimeout(10)

ack_checksum = str(ichecksum('ack'))
for j in range(5 - len(ack_checksum)): ack_checksum = '0' + ack_checksum

while True:
    seq_number = 0
    message = ''
    is_last_packet_received = False
    address = ()
    while not is_last_packet_received:
        while True:
            try:
                packet, address = udp_socket.recvfrom(1024)
                print(packet, address)
                data = str(packet, encoding='utf_8')
                if int(data[0]) == seq_number and ichecksum(data[6:], int(data[1:6])) == 0:
                    message += data[7:]
                    udp_socket.sendto(bytes(str(seq_number) + ack_checksum + 'ack', encoding='utf_8'), address)
                    print('ack ', seq_number, ' sent')
                    seq_number = (seq_number + 1)%2
                    if int(data[6]) == 1 :
                        is_last_packet_received = True
                else:
                    udp_socket.sendto(bytes(str((seq_number + 1)%2) + ack_checksum + 'ack', encoding='utf_8'), address)
                    print('ack ', (seq_number + 1)%2, ' sent')
                break
            except socket.timeout as e:
                None

    print('message: ', message)

    http_result = bytes()
    query = Query()
    queryAnswer = cacheDB.search((query.request == message))
    cacheAnswered = False

    if queryAnswer:
        print('request was cached!')
        http_result = bytes(queryAnswer[0]['response'], encoding='utf_8')
        cacheAnswered = True

    if not cacheAnswered:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = re.compile("Host: (.*?)\n").findall(message)[0]
        print('host: ',host)
        tcp_socket.connect((host, 80))
        tcp_socket.send(bytes(message, encoding='utf-8'))
        print('waiting for host ...')
        r = [None]
        while r:
            r,w,e = select.select([tcp_socket],[],[],3)
            if r:
                http_result += tcp_socket.recv(1024)
        print('http result: ', str(http_result, encoding='utf_8'))
        tcp_socket.close()
        http_result = base64.b64encode(http_result)
        cacheDB.insert({
            'request': message,
            'response': str(http_result, encoding='utf_8'),
        })
    
    inp = str(http_result, encoding='utf_8')

    packet = ''
    seq_number = 0
    total_packet_sent = 0
    success_packet_sent = 0
    for i in range(0, int(len(inp)/121) + 1):
        data = ''
        if i < int(len(inp)/121):
            data = inp[i*121 : i*121 + 121]
            data = '0' + data
        else:
            data = inp[i*121:]
            data = '1' + data
        
        checksum = str(ichecksum(data))
        for j in range(5 - len(checksum)): checksum = '0' + checksum
        packet = str(seq_number) + checksum + data
        packetStream = bytes(packet, encoding='utf_8')
        udp_socket.sendto(packetStream, address)
        total_packet_sent += 1
        acknowledged = False
        while not acknowledged:
            try:
                ack, address = udp_socket.recvfrom(1024)
                # print(ack, address)
                ack = str(ack, encoding='utf_8')
                if address == address and int(ack[0]) == seq_number and ichecksum(ack[6:], int(ack[1:6])) == 0 and ack[6:] == 'ack':
                    # print('ack ok!')
                    acknowledged = True
                    seq_number = (seq_number + 1)%2
                    success_packet_sent += 1
            except socket.timeout as e:
                print('timeout: ', e.args, ' resend packet!')
                udp_socket.sendto(packetStream, address)
                total_packet_sent += 1
    print('total packet sent: ', total_packet_sent)
    print('success_packet_sent: ', success_packet_sent)

    





