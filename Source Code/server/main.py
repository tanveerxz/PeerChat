# -*- coding: utf-8 -*-
"""
This is the main file for the server,
It handles all the connections with the clients and create chats
between two clients, The user data and chats are deleted when the
server is closed.
"""

import uuid
import socket
import pickle
import logging
from dependencies.modules.communicator import send, receive
from dependencies.modules.exceptionalthread import ThreadWithExc
from dependencies.modules.chat import Chat

users: list[dict] = []
threads: list[ThreadWithExc] = []
chats: list[Chat] = []

# This is the main connection of the server with the client that
# handles the creation of new chats, searching username, and changing
# client username.
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('', 8080))
server.listen()

# This is the connection of the server with the client that helps
# connect two clients temporarily before a chat connection is created.
server_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_.bind(('', 9090))
server_.listen()

logging.basicConfig(format=f'%(asctime)s [%(levelname)s] %(message)s')
logging.getLogger().setLevel(logging.INFO)


def get_username(_connection: socket.socket) -> str:
    """
    Gets the username from a given connection.
    :param _connection: The connection to get the username from.
    :return: The username of the client.
    """
    username = receive(_connection)
    if username in [user['username'] for user in users]:
        send('0', _connection)
        return get_username(_connection)
    send('1', _connection)
    return username


def find_user(address: str, mac: str) -> dict | None:
    """
    Finds a user by their address and mac address.
    :param address: The address of the user.
    :param mac: The mac address of the user.
    """
    for user in users:
        if user['address'] == address and user['mac'] == mac:
            return user
    return None


def handle_client(client: socket.socket, address: tuple[str, int]):
    """
    Function to handle a client connection.
    It handles the creation of new chats, searching username, and
    changing client username. This function is called when a new
    client connects to the server and is run in a separate thread to
    allow the main thread to accept new connections.
    :param client: The client socket.
    :param address: Address of the client.
    """
    try:
        mac = receive(client)
        # The user and their chat are identified by their
        # ip address and mac.
        user = find_user(address[0], mac)
        if user:
            send('1', client)
            logging.info(f'User reconnected({address}, {user["username"]})')  # noqa
        else:
            # Send 0 to indicate that the user is new.
            send('0', client)
            username = get_username(client)
            user_public_key = receive(client)
            user = {'id': str(uuid.uuid4()),
                    'address': address[0],
                    'mac': mac,
                    'username': username,
                    'key': user_public_key,
                    'chats': []
                    }
            users.append(user)
            logging.info(f'New user({address}, {username})')

        while True:
            # Wait for the client to connect to the second server.
            _connection = server_.accept()
            if _connection[1][0] == address[0]:
                break
        user['socket'] = _connection[0]

        send(pickle.dumps((user['username'], user['id'])), client, False)

        # Connect the user to their existing chats.
        for chat in user['chats']:
            chat.connect_user(user.copy())

        while True:
            # Wait for the client to choose an option.
            message = receive(client)
            # 0: Create new chat
            if message == '0':
                chat_with = receive(client)
                for user_2 in users:
                    if user_2['id'] == chat_with:
                        chat = Chat(user.copy(), user_2.copy())
                        user['chats'].append(chat)
                        user_2['chats'].append(chat)
                        chat.connect_user(user.copy())
                        chat.connect_user(user_2.copy())
                        chats.append(chat)
                        logging.info(f'New chat({user["username"]}, {user_2["username"]})')
                        break
            # 1: Search username
            elif message == '1':
                username = receive(client)
                possible_users: list[tuple] = []
                for user_2 in users:
                    if (username in user_2['username'] and
                            not user_2['username'] == user['username']):
                        _user = (user_2['username'], user_2['id'])
                        if username == user_2['username']:
                            possible_users.insert(0, _user)
                        else:
                            possible_users.append(_user)
                send(pickle.dumps(possible_users), client, False)
            # 2: Change username
            elif message == '2':
                old_username = user['username']
                new_username = get_username(client)
                user['username'] = new_username
                for chat in user['chats']:
                    _user = chat.user_1 if chat.user_1['id'] == user['id'] else chat.user_2
                    _user['username'] = new_username
                send(user['username'], client)
                logging.info(f'Username changed({old_username}, {new_username})')
            # 3: Disconnect
            elif message == '3':
                logging.info(f'User disconnected({user["username"]})')
                break
    except SystemExit:
        pass
    except Exception as error:
        logging.warning(error)


def listen_clients():
    """
    Listens to the clients for a connection.
    """
    try:
        while True:
            # Wait for new connections.
            connection = server.accept()
            # Create a new thread to handle the connection.
            _thread = ThreadWithExc(target=handle_client, args=connection)
            _thread.start()
            threads.append(_thread)
    except SystemExit:
        pass
    except Exception as error:
        logging.warning(error)


if __name__ == '__main__':
    logging.info(f'Server is running...')
    try:
        thread = ThreadWithExc(target=listen_clients)
        thread.start()
        threads.append(thread)
        while True:
            pass
    except KeyboardInterrupt:
        logging.info('Server is shutting down...')
        for thread in threads:
            thread.raiseExc(SystemExit)
        for _chat in chats:
            _chat.__delete__()
        server.close()
        server_.close()
        logging.info('Server has been stopped.')
