import base64
import socket

import pynetstring




def decode_response(response, remove_text="S "):
    return pynetstring.decode(response)[0].decode().replace(remove_text, "")


def sendMessagge(socket, message):
    socket.sendall(pynetstring.encode(message))


def upload(ip, port, nsfw, name, password, description, image_name):
    # encode image to base64
    with open(image_name, "rb") as img_file:
        image_64_encode = base64.b64encode(img_file.read()).decode('utf-8')

    sum_of_length = 0
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as first_channel:
        try:
            first_channel.connect((ip, int(port)))
        except socket.error as e:
            first_channel.close()
            return "E-> No response from server"
        #
        # The First phase
        #
        sendMessagge(first_channel, 'C MTP V:1.0')
        response = decode_response(first_channel.recv(1024))

        if response != "MTP V:1.0":
            sendMessagge(first_channel, 'E Client require -> \'S MTP V:1.0\', response from server -> \'' + response + '\'')
            first_channel.close()
            return "E-> Server does not support MTP V:1,0"

        first_channel.sendall(pynetstring.encode('C ' + name))
        token = decode_response(first_channel.recv(1024))
        port = decode_response(first_channel.recv(1024))

        if not validate_port(port):
            sendMessagge(first_channel, 'E Invalid port number \'' + port + '\'')
            first_channel.close()
            return "E-> Wrong response from server"

        #
        # The Second phase
        #
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as second_channel:
            try:
                second_channel.connect((ip, int(port)))
            except socket.error as e:
                sendMessagge(second_channel, 'E DataChannel is not responding on port -> \'' + port + '\'')
                first_channel.close()
                second_channel.close()
                return "E-> No response from DataChannel"

            second_channel.sendall(pynetstring.encode('C ' + name))
            token_r = decode_response(second_channel.recv(1024))

            if token != token_r:
                sendMessagge(second_channel,
                             'E The tokens do not match the first -> \'' + token_r + '\', the second -> \'' + token + '\'')
                first_channel.close()
                second_channel.close()
                return "E-> Wrong token!"

            data_type = ["REQ:meme", "REQ:password", "REQ:description", "REQ:isNSFW"]

            for type in data_type:

                response = decode_response(second_channel.recv(1024))

                if response != type:
                    sendMessagge(second_channel, 'E Client required -> ' + type + ' get -> \'' + response + '\'')
                    first_channel.close()
                    second_channel.close()
                    return "Error-> Server answer error!"

                second_channel.sendall(pynetstring.encode('C ' + image_64_encode))

                length = len(image_64_encode)
                sum_of_length += length

                response = decode_response(second_channel.recv(1024), "S ACK:")
                if int(response) != length:
                    sendMessagge(second_channel, 'E Bad length of data \'' + response + '\'')
                    first_channel.close()
                    second_channel.close()
                    return "E-> Wrong response from server"

            data = pynetstring.decode(second_channel.recv(1024))
            response = data[0].decode().replace("S ACK:", "")

            if not int(response) == length:
                sendMessagge(second_channel, 'E Bad length of data \'' + response + '\'')
                first_channel.close()
                second_channel.close()
                return "E-> Wrong response from server"

            dtoken = ""
            if len(data) == 2:  # end was sent with previous message
                dtoken = data[1].decode().replace("S END:", "")
            else:
                dtoken = pynetstring.decode(second_channel.recv(1024))[0].decode().replace("S END:", "")

            second_channel.close()

        #
        # The Third phase
        #
        response = decode_response(second_channel.recv(1024))
        if not sum_of_length == int(response):
            sendMessagge(first_channel, 'E Bad sum of length of data \'' + response + '\'')
            first_channel.close()
            return "E-> Wrong response from server"

        sendMessagge(first_channel, 'C ' + dtoken)

        response = pynetstring.decode(first_channel.recv(1024))[0].decode()

        if response[0] == 'E':
            first_channel.close()
            return "E-> Wrong token!"
        first_channel.close()

    return "Successfully uploaded!"


if __name__ == "__main__":
    upload('159.89.4.84', 42069, 'true', 'marcus', 'password', 'Some random message',
           '/home/marcushovi/Downloads/external-content.duckduckgo.com.png')
