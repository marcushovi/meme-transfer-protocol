import base64
import io
import re
import secrets
import socket
import string

import PySimpleGUI as sg
import names
import pynetstring
from PIL import Image


def decode_response(response, remove_text="S "):
    return pynetstring.decode(response)[0].decode().replace(remove_text, "")


def send_messagge(sckt, message):
    sckt.sendall(pynetstring.encode(message))


def upload_meme(host, port, name, password, nsfw, description, image_name, window):
    if nsfw:
        nsfw = 'true'
    else:
        nsfw = 'false'

    with open(image_name, "rb") as img_file:
        image_64_encode = base64.b64encode(img_file.read()).decode('utf-8')

    sum_of_length = 0
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as first_channel:
        try:
            first_channel.connect((host, int(port)))
        except socket.error as e:
            first_channel.close()
            window['-STATUS-'].update("E-> No response from server")
            window.refresh()
            return
        #
        # The First phase
        #
        window['-STATUS-'].update("The First phase")
        window.refresh()
        send_messagge(first_channel, 'C MTP V:1.0')
        response = decode_response(first_channel.recv(1024))

        if not response == "MTP V:1.0":
            send_messagge(first_channel,
                          'E Client require -> \'S MTP V:1.0\', response from server -> \'' + response + '\'')
            first_channel.close()
            window['-STATUS-'].update("E-> Server does not support MTP V:1,0")
            window.refresh()
            return

        send_messagge(first_channel, 'C ' + name)
        token = decode_response(first_channel.recv(1024))
        port = decode_response(first_channel.recv(1024))

        #
        # The Second phase
        #
        window['-STATUS-'].update("The Second phase")
        window.refresh()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as second_channel:
            try:
                second_channel.connect((host, int(port)))
            except socket.error as e:
                send_messagge(second_channel, 'E DataChannel is not responding on port -> \'' + port + '\'')
                first_channel.close()
                second_channel.close()
                window['-STATUS-'].update("E-> No response from DataChannel")
                window.refresh()
                return

            second_channel.sendall(pynetstring.encode('C ' + name))
            token_r = decode_response(second_channel.recv(1024))

            if token != token_r:
                send_messagge(second_channel,
                              'E The tokens do not match the first -> \'' + token_r + '\', the second -> \'' + token + '\'')
                first_channel.close()
                second_channel.close()
                window['-STATUS-'].update("E-> Wrong token!")
                window.refresh()
                return

            data = {"REQ:meme": image_64_encode, "REQ:password": password, "REQ:description": description,
                    "REQ:isNSFW": nsfw}

            window['-STATUS-'].update("Sending data")
            window.refresh()
            print("DATA")
            for key in data:

                response = decode_response(second_channel.recv(1024))

                if response != key:
                    send_messagge(second_channel, 'E Client required -> ' + key + ' get -> \'' + response + '\'')
                    first_channel.close()
                    second_channel.close()
                    window['-STATUS-'].update("Error-> Server answer error!")
                    window.refresh()
                    return

                window['-STATUS-'].update("Sending " + key)
                window.refresh()

                send_messagge(second_channel, 'C ' + data[key])

                length = len(data[key])
                sum_of_length += length

                response = decode_response(second_channel.recv(1024), "S ACK:")
                if int(response) != length:
                    send_messagge(second_channel, 'E Bad length of data \'' + response + '\'')
                    first_channel.close()
                    second_channel.close()
                    window['-STATUS-'].update("E-> Wrong response from server")
                    window.refresh()
                    return

            # data = pynetstring.decode(second_channel.recv(1024))
            # response = data[0].decode().replace("S ACK:", "")

            if int(response) != length:
                send_messagge(second_channel, 'E Bad length of data \'' + response + '\'')
                first_channel.close()
                second_channel.close()
                window['-STATUS-'].update("E-> Wrong response from server")
                window.refresh()
                return

            window['-STATUS-'].update("Data sent")

            dtoken = ""
            if len(data) == 2:  # end was sent with previous message
                dtoken = data[1].decode().replace("S END:", "")
            else:
                dtoken = decode_response(second_channel.recv(1024), "S END:")

            second_channel.close()

        #
        # The Third phase
        #
        window['-STATUS-'].update("The third phase")
        window.refresh()
        response = decode_response(first_channel.recv(1024))
        if sum_of_length != int(response):
            send_messagge(first_channel, 'E Bad sum of length of data \'' + response + '\'')
            first_channel.close()
            window['-STATUS-'].update("E-> Wrong response from server")
            window.refresh()
            return

        send_messagge(first_channel, 'C ' + dtoken)

        response = pynetstring.decode(first_channel.recv(1024))[0].decode()

        if response[0] == 'E':
            first_channel.close()
            window['-STATUS-'].update("E-> Wrong token!")
            return
        first_channel.close()

    window['-STATUS-'].update("Operation Successful")


sg.theme('DarkAmber')
left_section = [

    [

        sg.Text("IP address:"),

        sg.In(size=(25, 1), enable_events=True, key="-IP-", focus=True),

    ],

    [

        sg.Text("Port:"),

        sg.In(size=(25, 1), enable_events=True, key="-PORT-"),

    ],

    [

        sg.Text("Nick:"),

        sg.In(size=(25, 1), enable_events=True, key="-NICK-"),

        sg.Button("GENERATE name", size=(15, 1), key="-GENERATE NAME-")

    ],

    [

        sg.Text("Password:"),

        sg.In(size=(25, 1), enable_events=True, key="-PASSWORD-", password_char="*"),

        sg.Checkbox(text="Visible", enable_events=True, key="-IS PASS VISIBLE-"),

        sg.Button("GENERATE password", size=(20, 1), key="-GENERATE PASS-")

    ],

    [

        sg.Checkbox(text="NSFW", enable_events=True, key="-NSFW-"),

    ],

    [

        sg.Text("Description:"),

        sg.Multiline(size=(80, 10), enable_events=True, key="-DESCRIPTION-"),

    ],

]
right_section = [

    [

        sg.Text("Choose an image:"),

        sg.In(size=(80, 2), enable_events=True, key="-FILE-", readonly=True),

        sg.FileBrowse(file_types=(('Files', '*.jpeg'), ('Files', '*.png'), ('Files', '*.jpg'),)),

    ],

    [
        sg.Text("This is just preview, but the original image is uploaded to the server. Don't worry :d."),
    ],

    [

        sg.Image(key="-IMAGE-", size=(500, 500), subsample=2)

    ],

]

bottom_section = [

    [

        sg.Text(size=(80, 2), key="-STATUS-", text_color="orange"),

    ],

    [

        sg.Button("Send MEME", size=(10, 2), key="-SEND MEME-")

    ],

]

layout = [

    [

        sg.Column(left_section),

        sg.VSeperator(),

        sg.Column(right_section),

    ],

    [
        sg.HorizontalSeparator()
    ],

    [

        sg.Column(bottom_section)
    ]

]

window = sg.Window("MTP Client", layout, element_padding=(10))

# Run the Event Loop

while True:

    event, values = window.read()

    if event == "Exit" or event == sg.WIN_CLOSED:
        break

    if event == "-FILE-":  # A file was chosen from the listbox
        image = Image.open(values['-FILE-'])

        sub = .6
        if image.size[0] > 500 or image.size[0] > 500:
            sub = .15

        new_size = (int(int(image.size[0]) * sub), int(int(image.size[1]) * sub))

        resized_image = image.resize(new_size)
        buf = io.BytesIO()
        # format = values['-FILE-'][-3:].upper()
        # print(format)
        resized_image.save(buf, format="PNG")
        byte_image = buf.getvalue()

        image_64_encode = base64.b64encode(byte_image).decode('utf-8')

        window["-IMAGE-"].update(data=image_64_encode)

    if event == "-GENERATE NAME-":
        window["-NICK-"].update(names.get_first_name())

    if event == "-GENERATE PASS-":
        alphabet = string.ascii_letters + string.digits
        window["-PASSWORD-"].update(''.join(secrets.choice(alphabet) for i in range(10)))

    if event == "-IS PASS VISIBLE-":
        if not values["-IS PASS VISIBLE-"]:
            window["-PASSWORD-"].update(password_char="*")
        else:
            window["-PASSWORD-"].update(password_char="")

    if event == "-SEND MEME-":  # A file was chosen from the listbox

        regex_ip = "^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$"

        window['-STATUS-'].update('')

        # all inputs required
        # window['-STATUS-'].update('')
        # for key in values:
        #     if values[key] == '':
        #         window['-STATUS-'].update(key + " is required")
        #         is_valid = False
        #         break

        # validation
        if not values['-IP-'] != '':
            window['-STATUS-'].update("IP is required")

        elif not re.search(regex_ip, values['-IP-']):
            window['-STATUS-'].update("Invalid IP address")

        elif not values['-PORT-'] != '':
            window['-STATUS-'].update("PORT is required")

        elif not values['-PORT-'].isdigit():
            window['-STATUS-'].update("PORT needs to be digit")

        elif not values['-NICK-'] != '':
            window['-STATUS-'].update("NICK is required")

        elif not values['-PASSWORD-'] != '':
            window['-STATUS-'].update("PASSWORD is required")

        elif not values['-DESCRIPTION-'] != '':
            window['-STATUS-'].update("DESCRIPTION is required")

        elif not values['-FILE-'] != '':
            window['-STATUS-'].update("IMAGE is required")

        else:
            upload_meme(values['-IP-'], values['-PORT-'], values['-NICK-'], values['-PASSWORD-'], values['-NSFW-'],
                        values['-DESCRIPTION-'], values['-FILE-'], window)
        #
        # uploadMEME("159.89.4.84", 42070, "hovi", "asgahddfa", True, "True :d",
        #            "/home/marcushovi/Downloads/external-content.duckduckgo.com.jpg", window)

window.close()
