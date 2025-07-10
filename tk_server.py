import socket as sk
import threading
from utils import *
from database_models import *
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from cryptography_file import *
from typing import List


COMMANDS_FOR_SERVER = {
    "LOGIN",
    "LOGOUT",
    "CREATE",
    "READ",
    "UPDATE",
    "DELETE"
}

LOGGED_IN = dict()  # Username: sock


class Server:  # main socket
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = sk.socket(sk.AF_INET, sk.SOCK_STREAM)
        self.clients: List["ClientHandler"] = []

    def start(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"Server listening on {self.host}:{self.port}")
        database_manager = DatabaseManage('sqlite:///instance/website_database.db')

        while True:  # Accepts connections to new clients, handles each client
            client_sock, client_addr = self.sock.accept()
            print(f"New connection from {client_addr}")

            client_handler = ClientHandler(client_sock, self, database_manager)
            client_handler.start()
            self.clients.append(client_handler)

    def broadcast(self, message):
        for client in self.clients:
            if client.aes_key:
                client.handler_send(message)


class ClientHandler(threading.Thread):  # The socket for each client
    def __init__(self, sock: socket, server: "Server", database_manager: "DatabaseManage"):
        super().__init__()  # Calls the initialization of threading.Thread
        self.sock = sock
        self.server = server
        self.database_manager = database_manager
        self.username = None
        self.rsa_private_key, self.rsa_public_key = generate_rsa_keys()
        self.aes_key = None

    def server_exchange_keys(self):
        print("server_exchange_keys()")
        try:
            self.sock.send(self.rsa_public_key)
            encrypted_aes_key = self.sock.recv(2048)
            aes_key = rsa_decrypt(self.rsa_private_key, encrypted_aes_key)

            # Check if the key length is valid for AES (16, 24, or 32 bytes)
            if len(aes_key) not in [16, 24, 32]:
                return [False, "Invalid AES key length"]

            # Perform a test encryption-decryption cycle using ECB mode
            test_data = b'Test Data'
            encrypted_test = aes_encrypt(aes_key, test_data)
            decrypted_test = aes_decrypt(aes_key, encrypted_test)

            if test_data != decrypted_test:
                print("AES key is invalid or corrupted")
                return [False, "AES key is invalid or corrupted"]

            self.aes_key = aes_key
            return [True]

        except ConnectionError:
            print(f"ConnectionError while handling client: {self.sock.getpeername()[0]}")
            self.sock.close()
            return [False, "ConnectionError while handling client"]

        except Exception as e:
            print(e)
            return [False, f"Failed to validate AES key: {e}"]

    def run(self):
        while not self.aes_key:  # Keys Exchange
            try:
                message_info = self.sock.recv(2048)
                message = message_info.decode()
                if message == "GetPublicKey":
                    self.server_exchange_keys()  # attempt for key exchange
                else:
                    self.sock.send("Error" + "|" + "Keys exchange needed, send request for public key ('GetPublicKey')")
            except ConnectionError:
                print(f"ConnectionError while handling client: {self.sock.getpeername()[0]}")
                self.sock.close()
                return
            except UnicodeDecodeError:
                pass

        while True:
            try:
                full_message_validity = self.handler_receive()  # [0]: T/F for 'Was there an error?' [1]: the message
                if full_message_validity[0] == "Error":
                    if full_message_validity[1] == "ConnectionError":
                        print(f"ConnectionError while handling client: {self.sock.getpeername()[0]}")
                        break
                    self.handler_send("Error" + "|" + full_message_validity[1])
                else:
                    full_message = full_message_validity[1]
                    command, message = get_command_by_protocol(full_message)
                    # If there's no valid command, the function returns 'Error' and the list of valid commands
                    if command == "Error":
                        self.handler_send("Error" + "|" + message)
                    else:
                        self.handle_command(command, message)
            except ConnectionError:
                print(f"ConnectionError while handling client: {self.sock.getpeername()[0]}")
                break
        print(f"Closed connection with {self.sock.getpeername()[0]}")
        self.sock.close()
        self.server.clients.remove(self)
        if self.username:
            del LOGGED_IN[self.username]

    def handler_send(self, message):
        print(f"Sending to {self.sock.getpeername()}: {message}")
        sending(self.sock, message, self.aes_key)

    def handler_receive(self):
        received = receiving(self.sock, self.aes_key)
        if received[0] == "Success":
            print(f"Received from {self.sock.getpeername()}: {received[1]}")
        return received

    def handle_command(self, command, message):
        if self.username not in LOGGED_IN.keys():
            if command == "LOGIN":
                self.handle_login(message)
            else:
                self.handler_send("Error" + '|' + "You must log in first")
            return
        if command == "LOGIN":
            self.handler_send('Error' + '|' + f'You are already logged in as {self.username}')
        elif command == "LOGOUT":
            self.logout()
        else:
            self.handle_crud(command, message)

    def login(self, Username, Password):
        session = self.database_manager.session
        existing_admin = session.query(Admin).filter_by(AdminUsername=Username).first()
        if not existing_admin:
            self.handler_send("Error" + '|' + 'No Admin with that username')
            return

        if existing_admin.AdminPassword == encrypt_password(Password):
            if Username in LOGGED_IN.keys():
                self.handler_send("Error" + '|' + 'Admin already logged in...')
                return
            self.username = Username
            LOGGED_IN[Username] = self.sock
            self.handler_send("Success" + '|' + 'Login succeeded')
        else:
            self.handler_send("Error" + '|' + 'Incorrect password')
            return

    def logout(self):
        del LOGGED_IN[self.username]
        self.handler_send('Success' + '|' + 'Logout succeeded')

    def handle_login(self, message):
        if '|' not in message:
            self.handler_send('Error' + '|' + 'Login requires username and password, separated by "|"')
            return
        Username, Password = message.split('|', 1)
        self.login(Username, Password)

    def handle_crud(self, command, message):
        try:
            table_name, rest_of_message = message.split("|", 1)
        except ValueError:
            self.handler_send("Error" + '|' + "message should have table name and then rest of the message,"
                                              " separated by a '|'")
            return

        if command in ("READ", "DELETE", "UPDATE"):
            if "|" in rest_of_message:
                text_id, rest_of_message = rest_of_message.split("|", 1)
            else:
                text_id = rest_of_message
            if not text_id.isdigit():
                self.handler_send("Error" + '|' + "id should be an integer")
                return
            id = int(text_id)

        if command in ("CREATE", "UPDATE"):
            values_dict_message = rest_of_message
            values_dict_list = text_to_dictionary(values_dict_message)
            if values_dict_list[0] == "Error":
                self.handler_send("Error" + '|' + values_dict_list[1])
                return
            values_dict = values_dict_list[1]

        if command == "CREATE":
            success_dict = self.database_manager.create_row(table_name, values_dict)
        elif command == "READ":
            success_dict = self.database_manager.read_row(table_name, id)
        elif command == "UPDATE":
            success_dict = self.database_manager.update_row(table_name, id, values_dict)
        elif command == "DELETE":
            success_dict = self.database_manager.delete_row(table_name, id)

        if success_dict['success']:
            if command == "READ":
                self.handler_send(f'Success' + '|' + success_dict["table_name"] + '|'
                                  + dictionary_to_text(success_dict["values"]))
            else:
                self.handler_send('Success' + '|' + 'the command succeeded')
        else:
            self.handler_send('Error' + '|' + success_dict['message'])


class DatabaseManage:  # Class for managing the database
    def __init__(self, database_uri):
        self.engine = create_engine(database_uri)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def create_row(self, table_name, values_dict):
        try:
            if table_name in MAIN_TABLES.keys():
                table_and_checker_dict = MAIN_TABLES[table_name]
            elif table_name in RELATIONSHIP_TABLES.keys():
                table_and_checker_dict = RELATIONSHIP_TABLES[table_name]
            else:
                return {"success": False, "message": "There is no such table."}

            excess_columns_dict = excess_columns_check(table_name, values_dict)
            if not excess_columns_dict["is_valid"]:
                return {"success": False, "message": excess_columns_dict["message"]}
            if "id_for_updating" in values_dict:
                return {"success": False, "message": "create command shouldn't get an id for updating"}
                # id_for_updating is not considered as excess information at the excess_column_check()
                # But that value is excess for Create command, as there's no such column in the tables.
                # Also, having such value at create could bypass the limitation on double usernames, emails etc.

            table = table_and_checker_dict["table"]
            input_check_dict = table_and_checker_dict["input_check"](self.session, **values_dict)
            if not input_check_dict["is_valid"]:
                return {"success": False, "message": input_check_dict["message"]}

            with self.session.begin_nested():
                if table == Participant:  # If there's a join request from that user to the activity, delete it
                    existing_request = self.session.query(JoinRequest).filter_by(**values_dict).first()
                    if existing_request:
                        self.session.delete(existing_request)

                if table == Activity:  # The date needs to be replaced with a python date object.
                    try:
                        ActivityDate = values_dict["ActivityDate"]
                        if ActivityDate:
                            values_dict["ActivityDate"] = datetime.strptime(ActivityDate, '%Y-%m-%d').date()
                    except KeyError:
                        pass

                if table == Category:
                    values_dict["CategoryName"] = values_dict["CategoryName"].lower()

                if table == User:
                    values_dict["Password"] = encrypt_password(values_dict["Password"])

                new_row = table(**values_dict)  # create the new row of the table with the values from the values_dict
                self.session.add(new_row)  # add the row to the table
                self.session.commit()
                return {"success": True}
        except SQLAlchemyError as e:
            if table_name == "Participant":
                self.session.rollback()  # Rollback any pending transactions
            print("Database error at create_row", str(e))
            return {"success": False, "message": "Database error"}

    def read_row(self, table_name, id):
        try:
            if table_name not in MAIN_TABLES.keys() and table_name not in RELATIONSHIP_TABLES.keys():
                return {"success": False, "message": "There is no such table."}
            table_info = MAIN_TABLES[table_name] if table_name in MAIN_TABLES.keys() \
                else RELATIONSHIP_TABLES[table_name]
            table = table_info["table"]
            dict_for_id = {table_name + 'ID': id}
            row_to_read = self.session.query(table).filter_by(**dict_for_id).first()
            if not row_to_read:
                return {"success": False, "message": f"No {table_name} for id: {id}"}

            values_dict = {}
            columns = table_info["columns"]
            row_id = table_name + "ID"
            values_dict[row_id] = str(getattr(row_to_read, row_id))
            for column in columns:
                values_dict[column] = str(getattr(row_to_read, column))
            if table == User:
                values_dict["Password"] = "********"
            return {"success": True, "table_name": table_name, "values": values_dict}
        except SQLAlchemyError as e:
            print("Database error at read_row", str(e))
            return {"success": False, "message": "Database error"}

    def update_row(self, table_name, id, values_dict):  # Should receive the values they want to change
        try:
            if table_name not in MAIN_TABLES.keys() and table_name not in RELATIONSHIP_TABLES.keys():
                return {"success": False, "message": "There is no such table."}
            table_info = MAIN_TABLES[table_name] if table_name in MAIN_TABLES.keys() \
                else RELATIONSHIP_TABLES[table_name]
            table = table_info["table"]
            dict_for_id = {table_name + 'ID': id}
            row_to_update = self.session.query(table).filter_by(**dict_for_id).first()
            if not row_to_update:
                return {"success": False, "message": f"No {table_name} for id: {id}"}

            updated_values_dict = {}
            columns = table_info["columns"]
            for column in columns:  # get the current values
                current_value = getattr(row_to_update, column)
                updated_values_dict[column] = current_value if current_value is None else str(current_value)
            for value_name in values_dict.keys():
                updated_values_dict[value_name] = values_dict[value_name]  # update what is asked for by the admin
            updated_values_dict["id_for_updating"] = id

            if table_name == "Activity":
                try:
                    if updated_values_dict["AgeRangeMax"] == "None":  # A way to cancel age range maximum
                        updated_values_dict["AgeRangeMax"] = None
                except KeyError:
                    pass
                try:
                    if updated_values_dict["AgeRangeMin"] == "None":  # A way to remove age range minimum
                        updated_values_dict["AgeRangeMin"] = None
                except KeyError:
                    pass

            excess_columns_dict = excess_columns_check(table_name, updated_values_dict)
            if not excess_columns_dict["is_valid"]:
                return {"success": False, "message": excess_columns_dict["message"]}

            if table_name in MAIN_TABLES.keys():
                updated_values_dict["Deleted"] = boolean_check(updated_values_dict["Deleted"])["value"]

            updated_input_check_dict = table_info["input_check"](self.session, **updated_values_dict)
            if not updated_input_check_dict["is_valid"]:
                if updated_input_check_dict["message"] == "Email already used":
                    used_email_user = self.session.query(User).filter_by(Email=updated_values_dict["Email"]).first()
                    if int(used_email_user.UserID) == int(row_to_update.UserID):
                        pass  # Email 'already used' by that user... not a problem
                    else:
                        return {"success": False, "message": updated_input_check_dict["message"]}
                else:
                    return {"success": False, "message": updated_input_check_dict["message"]}

            if table == Participant:  # If there's a join request from that user to the activity, delete it
                existing_request = self.session.query(JoinRequest).filter_by(**updated_values_dict).first()
                if existing_request:
                    self.session.delete(existing_request)

            if table == Activity:
                ActivityDate = updated_values_dict["ActivityDate"]
                if ActivityDate:
                    updated_values_dict["ActivityDate"] = datetime.strptime(ActivityDate, '%Y-%m-%d').date()

            if table == Category:
                updated_values_dict["CategoryName"] = updated_values_dict["CategoryName"].lower()

            if table == User:
                try:
                    values_dict["Password"] = encrypt_password(values_dict["Password"])
                except KeyError or ValueError:
                    pass

            for column, value in updated_values_dict.items():
                setattr(row_to_update, column, value)  # The actual update of the values in the row
            self.session.commit()
            return {"success": True}

        except SQLAlchemyError as e:
            print("Database error at update_row", str(e))
            return {"success": False, "message": "Database error"}

    def delete_row(self, table_name, id):
        try:
            if table_name not in MAIN_TABLES.keys() and table_name not in RELATIONSHIP_TABLES.keys():
                return {"success": False, "message": "There is no such table."}
            table = MAIN_TABLES[table_name]["table"] if table_name in MAIN_TABLES.keys() \
                else RELATIONSHIP_TABLES[table_name]["table"]

            # Each table's id has a different name, so each table has different arguments for the filter function,
            # That's a problem for the generic filtering.
            # '**dict' solves that problem by telling the key-value pairs in the dictionary should be
            # treated as named arguments to a function call.
            dict_for_id = {table_name + 'ID': id}
            row_to_delete = self.session.query(table).filter_by(**dict_for_id).first()
            if not row_to_delete:
                return {"success": False, "message": f"No {table_name} for id: {id}"}

            if table_name in MAIN_TABLES.keys():
                row_to_delete.Deleted = True  # Soft deletion (Avoids reuse of the id of the deleted row)
                self.session.commit()
                return {"success": True}
            else:
                self.session.delete(row_to_delete)  # Normal deletion
                self.session.commit()
                return {"success": True}
        except SQLAlchemyError as e:
            print("Database error at delete_row", str(e))
            return {"success": False, "message": "Database error"}


if __name__ == "__main__":
    server = Server('192.168.1.147', 12345)
    server.start()
