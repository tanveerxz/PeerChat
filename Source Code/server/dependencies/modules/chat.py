# -*- coding: utf-8 -*-
"""
This module contains the class for a chat between two clients.
Creating an object for each chat enables us to create multiple chats
at once on the server side.
"""

from datetime import datetime
import socket
import pickle
import logging
import pytz
from dependencies.modules.communicator import send, receive  # noqa
from dependencies.modules.exceptionalthread import ThreadWithExc  # noqa
from random_open_port import random_port


class Chat:
    """Main class for a chat on the server."""

    def __init__(self, user_1: dict, user_2: dict):
        self.user_1 = user_1
        self.chat_server_user_1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.user_2 = user_2
        self.chat_server_user_2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.user_1_port = random_port()
        self.chat_server_user_1.bind(('', self.user_1_port))
        self.chat_server_user_1.listen()
        self.user_2_port = random_port()
        self.chat_server_user_2.bind(('', self.user_2_port))
        self.chat_server_user_2.listen()
        self.chat: list = []
        self.listen_user_1_thread: ThreadWithExc = None
        self.listen_user_2_thread: ThreadWithExc = None
        self.listen_message_user_1_thread: ThreadWithExc = None
        self.listen_message_user_2_thread: ThreadWithExc = None
        self.user_1_unread = False
        self.user_2_unread = False

    def __delete__(self):
        """Deletes the chat object."""
        for thread in [self.listen_user_1_thread, self.listen_user_2_thread,
                       self.listen_message_user_1_thread, self.listen_message_user_2_thread]:
            if thread:
                thread.raiseExc(SystemExit)

    def connect_user(self, user):
        """
        Connects a user to the chat.
        :param user: The user to be connected to the chat.
        """
        try:
            # Send the port to the user to connect to the
            # chat connection with the server, Then listen
            # to the user for a connection with the chat
            # server.
            if self.user_1['id'] == user['id']:
                send(str(self.user_1_port), user['socket'])
                self.listen_user_1_thread = ThreadWithExc(
                    target=self.listen_user, args=(user,))
                self.listen_user_1_thread.start()
            elif self.user_2['id'] == user['id']:
                send(str(self.user_2_port), user['socket'])
                self.listen_user_2_thread = ThreadWithExc(
                    target=self.listen_user, args=(user,))
                self.listen_user_2_thread.start()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as error:
            logging.warning('connect_user: ' + str(error))

    def listen_user(self, user: dict):
        """
        Listens to a user for a connection with the chat server.
        :param user: The user to listen to for a connection.
        """
        try:
            if user['id'] == self.user_1['id']:
                chat_server = self.chat_server_user_1
                other_user = self.user_2
                unread = self.user_1_unread
            else:
                chat_server = self.chat_server_user_2
                other_user = self.user_1
                unread = self.user_2_unread
            while True:
                connection = chat_server.accept()
                if connection[1][0] == user['address']:
                    user['socket'] = connection[0]

                    # Send the other user's details to the user.
                    send(pickle.dumps((other_user['username'], other_user['key'],
                                       other_user['id'])), user['socket'], False)
                    # Send the user that started the chat.
                    send(self.user_1['id'], user['socket'])
                    # Send the unread status to the user.
                    send(pickle.dumps(unread), user['socket'], False)

                    # Send the existing chat to the user.
                    if self.chat:
                        # Send 1 to indicate that the chat exists.
                        send('1', user['socket'])
                        send(pickle.dumps(self.chat), user['socket'], False)
                    else:
                        # Send 1 to indicate that the chat exists.
                        send('0', user['socket'])

                    # Listen to the user for a message.
                    thread = ThreadWithExc(target=self.listen_message, args=(user,))
                    thread.start()

                    if user['id'] == self.user_1['id']:
                        self.user_1 = user
                        if self.listen_message_user_1_thread:
                            self.listen_message_user_1_thread.raiseExc(SystemExit)
                        self.listen_message_user_1_thread = thread
                    else:
                        self.user_2 = user
                        if self.listen_message_user_2_thread:
                            self.listen_message_user_2_thread.raiseExc(SystemExit)
                        self.listen_message_user_2_thread = thread
                    break
        except (SystemExit, BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as error:
            logging.warning('listen_user: ' + str(error))

    def listen_message(self, user: dict):
        """
        Listens to a user for a message.
        :param user:
        """
        while True:
            try:
                message = receive(user['socket'])
                if message == '__170523Read170523__':
                    if user['id'] == self.user_1['id']:
                        self.user_1_unread = False
                    else:
                        self.user_2_unread = False
                    continue
                self.add_message(message, user['id'])
                if user['id'] == self.user_1['id']:
                    self.user_2_unread = True
                    _user = self.user_2
                else:
                    self.user_1_unread = True
                    _user = self.user_1
                send(pickle.dumps(self.chat[-1]), _user['socket'], False)
            except SystemExit:
                break
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
            except Exception as error:
                logging.warning('listen_message: ' + str(error))

    def add_message(self, message: str, _id: str):
        """
        Adds a message to the chat.
        :param message: The message to be added.
        :param _id: Message sender's id.
        """
        self.chat.append((message, _id,
                          datetime.now(pytz.timezone("Asia/Kolkata")).strftime('%D::%H:%M')))
        if len(self.chat) > 100:
            self.chat.pop(0)
