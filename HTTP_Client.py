import socket
import base64
import re


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

ack_checksum = str(ichecksum('ack'))
for j in range(5 - len(ack_checksum)): ack_checksum = '0' + ack_checksum

inp = ""
while True:
    temp = input()
    if temp == 'end':
        break
    inp+=temp+"\n"

mySocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
mySocket.settimeout(10)
proxyAdress = ('127.0.0.1', 80)

while True:
    packet = '' 
    seq_number = 0
    for i in range(0, int(len(inp)/121) + 1):
        data = ''
        if i < int(len(inp)/121):
            data = inp[i*121 : i*121 + 120]
            data = '0' + data
        else:
            data = inp[i*121:]
            data = '1' + data
        
        checksum = str(ichecksum(data))
        for j in range(5 - len(checksum)): checksum = '0' + checksum
        packet = str(seq_number) + checksum + data
        packetStream = bytes(packet, encoding='utf_8')
        mySocket.sendto(packetStream, proxyAdress)
        acknowledged = False
        while not acknowledged:
            try:
                ack, address = mySocket.recvfrom(1024)
                # print(ack, address)
                ack = str(ack, encoding='utf_8')
                if address == proxyAdress and int(ack[0]) == seq_number and ichecksum(ack[6:], int(ack[1:6])) == 0 and ack[6:] == 'ack':
                    # print('ack ok!')
                    acknowledged = True
                    seq_number = (seq_number + 1)%2
            except socket.timeout as e:
                print('timeout: ', e.args, ' resend packet!')
                mySocket.sendto(packetStream, proxyAdress)

    seq_number = 0
    message = ''
    is_last_packet_received = False
    address = ()
    total_packet_receved = 0
    healthy_packet_receved = 0
    while not is_last_packet_received:
        while True:
            try:
                packet, address = mySocket.recvfrom(1024)
                total_packet_receved += 1
                data = str(packet, encoding='utf_8')
                if int(data[0]) == seq_number and ichecksum(data[6:], int(data[1:6])) == 0:
                    healthy_packet_receved += 1
                    message += data[7:]
                    mySocket.sendto(bytes(str(seq_number) + ack_checksum + 'ack', encoding='utf_8'), address)
                    # print('ack ', seq_number, ' sent')
                    seq_number = (seq_number + 1)%2
                    if int(data[6]) == 1 :
                        is_last_packet_received = True
                else:
                    mySocket.sendto(bytes(str((seq_number + 1)%2) + ack_checksum + 'ack', encoding='utf_8'), address)
                    print('ack ', (seq_number + 1)%2, ' resend')
                break
            except socket.timeout as e:
                None

    print('total packet receved: ', total_packet_receved)
    print('healthy packet receved: ', healthy_packet_receved)

    message = base64.b64decode(message)
    message = str(message, encoding='utf_8')
    if len(message) == 0:
        print('message result is empty! plz check your connection.')
    message_header, message_body = message.split('\n\r', 1)

    if '301' in message_header or '302' in message_header:
            index = message_header.find('Location: ')
            location = message_header[index + 10:message_header.find('\n', index)]
            print('redirected to', location)
            new_host = location[7:location.find('/', 7)]
            new_url = location[location.find('/', 7):-1]
            inp = 'GET ' + new_url + ' HTTP/1.1\nHost: ' + new_host + '\n\n'
            print('new req is: ', inp)
            continue


    print('result saved in result.html!')
    with open('result.html','wb') as f:
        f.write(bytes(message_body, encoding='utf_8'))
    
    break

