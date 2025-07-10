import tkinter as tk
from tkinter import messagebox
import socket as sk
from utils import *
from database_models import MAIN_TABLES, RELATIONSHIP_TABLES
from cryptography_file import *


class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = sk.socket(sk.AF_INET, sk.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        print(f"Client communicates with {self.host}:{self.port}")
        self.aes_key = None
        self.client_exchange_keys()

    def client_exchange_keys(self):
        self.socket.send("GetPublicKey".encode())
        public_key_data = self.socket.recv(2048)
        public_key = RSA.importKey(public_key_data)
        self.aes_key = generate_aes_key()
        encrypted_aes_key = rsa_encrypt(public_key, self.aes_key)
        self.socket.send(encrypted_aes_key)

    def send_message(self, message):
        if not self.aes_key:
            raise ValueError("AES key not exchanged")
        print("Sending to server:", message)
        return sending(self.socket, message, self.aes_key)

    def receive_message(self):
        if not self.aes_key:
            raise ValueError("AES key not exchanged")
        received = receiving(self.socket, self.aes_key)  # a list with two variables - success message and message
        if received[0] == "Success":
            print("Received from server:", received[1])
        else:
            print("Connection Error")
        return received

    def close_connection(self):
        self.socket.close()


class GUI:
    def __init__(self, client: "Client"):
        self.client = client
        self.root = tk.Tk()
        self.root.title("Website Admin GUI")
        self.root.geometry("300x450")

        # Variables for storing user input
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.selected_command_var = tk.StringVar()
        self.selected_table_var = tk.StringVar()

        # Create login window
        self.create_login_window()

    def create_login_window(self):
        self.clear_window()

        # Login form
        tk.Button(self.root, text="Exit", command=self.root.destroy).pack()
        tk.Label(self.root, text="Username:").pack()
        tk.Entry(self.root, textvariable=self.username_var).pack()
        tk.Label(self.root, text="Password:").pack()
        tk.Entry(self.root, textvariable=self.password_var, show="*").pack()
        tk.Button(self.root, text="Login", command=self.login).pack()

    def login(self):
        username = self.username_var.get()
        password = self.password_var.get()
        login_message = "LOGIN" + '|' + username + '|' + password
        self.client.send_message(login_message)

        server_response = self.client.receive_message()
        success_message, response_message = self.handle_server_response(*server_response)
        if success_message == "Success":
            self.create_logged_in_window()
        else:
            messagebox.showerror("Error", response_message)

    def logout(self):
        self.client.send_message("LOGOUT")
        response = self.client.receive_message()
        success_message, response_message = self.handle_server_response(*response)
        if success_message == "Success":
            self.create_login_window()
        else:
            messagebox.showerror("Error", f"{response_message}.\n you can just close the window")

    def create_logged_in_window(self):
        self.clear_window()

        tk.Button(self.root, text="Logout", command=self.logout).pack()
        # LoggedIn window with CRUD command selection
        commands = ["Create", "Read", "Update", "Delete"]
        tk.Label(self.root, text="Select a command:").pack()
        tk.OptionMenu(self.root, self.selected_command_var, *commands).pack()
        tables = ["User", "Activity", "Category", "City", "Participant", "JoinRequest", "UserCategory",
                  "ActivityCategory"]
        tk.Label(self.root, text="Select a table:").pack()
        tk.OptionMenu(self.root, self.selected_table_var, *tables).pack()
        tk.Button(self.root, text="Submit", command=self.submit_command_and_table).pack()

    def submit_command_and_table(self):
        selected_command = self.selected_command_var.get()
        selected_table = self.selected_table_var.get()
        if not selected_command or not selected_table:
            messagebox.showerror("Error", "You need to choose a table and a command")
        else:
            self.create_crud_request_window(selected_command, selected_table)

    def create_crud_request_window(self, selected_command, selected_table):
        self.clear_window()

        # Add an escape button to return to logged_in window
        tk.Button(self.root, text="Back", command=self.create_logged_in_window).pack()

        # Add an ID entry if the command requires it
        if selected_command in {"Read", "Update", "Delete"}:
            tk.Label(self.root, text="Enter ID:").pack()
            id_entry = tk.Entry(self.root, name="id_entry")
            id_entry.pack()

        # Add entry fields for each column if the command is Create or Update
        columns_to_retrieve = ()
        if selected_command in {"Create", "Update"}:
            columns_to_retrieve = MAIN_TABLES[selected_table]["columns"] if \
                selected_table in MAIN_TABLES.keys() else RELATIONSHIP_TABLES[selected_table]["columns"]
            entry_widgets_for_values = {}
            for column in columns_to_retrieve:
                tk.Label(self.root, text=column).pack()

                entry_widget = tk.Entry(self.root, name=f"{column.lower()}_entry")
                entry_widget.pack()
                entry_widgets_for_values[column] = entry_widget


        # Add a submit button with the name of the command
        tk.Button(self.root, text=selected_command, command=lambda: self.
                  submit_command(selected_command, selected_table, columns_to_retrieve)).pack()

    def submit_command(self, selected_command, selected_table, columns_to_retrieve):
        # Retrieve input values
        row_id = None
        if selected_command in {"Read", "Update", "Delete"}:
            id_entry = self.root.nametowidget("id_entry")
            row_id = id_entry.get()

        # columns will be empty for READ and Delete where there are no column entries
        entry_widgets = {column: self.root.nametowidget(f"{column.lower()}_entry") for column in columns_to_retrieve}
        values = {}
        for column, entry_widget in entry_widgets.items():
            value = entry_widget.get()
            if value:
                values[column] = value

        # Construct message
        message = f"{selected_command.upper()}|{selected_table}|{row_id + '|' if row_id else ''}"
        message += "|".join([f"{len(column) + len(value) + 2}{column}:{value}" for column, value in values.items()])

        # Send message to server
        self.client.send_message(message)

        response = self.client.receive_message()
        success_message, response_message = self.handle_server_response(*response)
        if success_message == "Success":
            # Clear entry widgets if succeeded
            if row_id:
                id_entry.delete(0, tk.END)
            for column, entry_widget in entry_widgets.items():
                entry_widget.delete(0, tk.END)

            if selected_command != "Read":
                messagebox.showinfo("Success", response_message)
            else:
                if "|" not in response_message:
                    messagebox.showerror("Error", "Server's response isn't by protocol - "
                                                  "no '|' that separates table name and values, "
                                                  "this is their response:\n" + response_message)
                table_name, text_values_dict = response_message.split('|', 1)
                values_dict_list = text_to_dictionary(text_values_dict)
                if values_dict_list[0] == "Success":
                    values_dict = values_dict_list[1]
                    message_to_show = f"{table_name}\n\n"
                    for key, value in values_dict.items():
                        message_to_show += f"{key} - {value}\n"
                    messagebox.showinfo("Success", message_to_show)
                else:
                    messagebox.showerror("Error", "Server's response isn't by protocol - "
                                                  "their dictionary has flaws, "
                                                  "this is their response:\n" + response_message)

        else:
            # Handle error
            messagebox.showerror("Error", response_message)


    def handle_server_response(self, success_message, response_message):
        if success_message != "Success":
            return ["Error", "Error while receiveing response from the server"]

        if '|' not in response_message:
            print("Error - Server sent message not according to the protocol")
            return ["Error", "Server's message isn't according to the protocol - no '|' separation"]

        second_success_message, message = response_message.split('|', 1)

        if second_success_message == "Error":
            return ["Error", message]
        elif second_success_message == "Success":
            return ["Success", message]
        else:
            return ["Error", "Server sent message not according to the protocol - no Success/Error"]

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def start(self):
        self.root.mainloop()


if __name__ == "__main__":
    host = '127.0.0.1'
    port = 12345
    client = Client(host, port)
    gui = GUI(client)
    gui.start()
