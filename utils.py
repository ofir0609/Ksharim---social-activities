from socket import socket
from cryptography_file import *

LENG_LEN_MESSAGE = 5

COMMANDS = {
    "LOGIN",
    "LOGOUT",
    "CREATE",
    "READ",
    "UPDATE",
    "DELETE"
}


def sending(client_socket: socket, original_text: str, aes_key):
    try:
        info = original_text.encode()
        encrypted_info = aes_encrypt(aes_key, info)

        str_length = str(len(encrypted_info))
        str_length = str_length.zfill(LENG_LEN_MESSAGE)
        complete_encrypted_message = str_length.encode() + encrypted_info

        client_socket.send(complete_encrypted_message)
        return "Success"
    except ConnectionError:
        print("Connection error at sending")
        return "Error"


def receiving(client_socket: socket, aes_key):
    try:
        info_length = client_socket.recv(LENG_LEN_MESSAGE)
        if not info_length.isdigit():
            return ["Error", "communication not according to the protocol"]

        int_length = int(info_length.decode())
        encrypted_info = client_socket.recv(int_length)
        info = aes_decrypt(aes_key, encrypted_info)
        original_text = info.decode()

        return ["Success", original_text]
    except ConnectionError:
        print("Connection error at receiving")
        return ["Error", "ConnectionError"]


def dictionary_to_text(values_dict):
    # Written in an odd way in order not finish with "|", and then adjust the length too.
    text_dict = ""
    to_add = []
    for key, value in values_dict.items():
        text_dict += "".join(to_add)
        length = len(key + ":" + value + "|")
        to_add = [str(length), key, ":", value, "|"]
    to_add[0] = str(int(to_add[0])-1)
    text_dict += "".join(to_add)
    if text_dict != "":
        text_dict = text_dict[:-1]
    return text_dict


def text_to_dictionary(text_dict: str):
    dictionary = dict()
    while text_dict != "":
        key_value_len = number_from_beginning_of_string(text_dict)
        text_dict = text_dict[len(str(key_value_len)):]
        if key_value_len == 0:
            return ["Error", "Invalid dictionary, a key-value pair needs to have length before of it"]
        key_value = text_dict[:key_value_len]
        text_dict = text_dict[key_value_len:]
        if ":" not in key_value:
            return ["Error", "Invalid dictionary, ':' is missing"]
        if text_dict != "" and not key_value.endswith("|"):
            return ["Error", 'Invalid dictionary - key-value pairs should be separated with "|"']
        key, value = key_value.split(":", 1)
        if text_dict != "":
            value = value[:-1]  # There's a '|' to get rid of
        if key not in dictionary.keys():
            dictionary[key] = value  # Adds key value to dictionary
        else:
            return ["Error", f"Invalid dictionary - '{key}' key repeats itself"]
    return ["Success", dictionary]

def number_from_beginning_of_string(string: str):
    number = 0
    for character in string:
        if not character in "0123456789":
            return number
        number = number * 10 + int(character)
    return number


def get_command_by_protocol(full_message: str):
    print("full_message: ", full_message)
    if full_message == "LOGOUT":
        return ["LOGOUT", ""]
    if full_message in COMMANDS:
        return ["Error", "This command needs values"]
    command = ""
    message = ""
    for defined_command in COMMANDS:
        if full_message.startswith(defined_command + "|"):
            command, message = full_message.split('|', 1)
    if command == "":
        return ["Error", f"These are the valid commands: {COMMANDS}. if there are values, they should come after a '|'"]
    return [command, message]