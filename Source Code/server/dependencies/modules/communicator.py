# -*- coding: utf-8 -*-
"""
This module contains the functions for sending and receiving messages
between two sockets.
"""

import socket

header = 64
encoding = 'utf-8'


def send(message: str | bytes, connection: socket.socket, encode=True):
    """

    Sends a message to the given connection.
    It is important to note that the message is sent in two parts:
    1. The length of the message.
    2. The message itself.
    :param message: The message to send.
    :param connection: Connection to send the message to
    :param encode: Whether to encode the message or not.
    """
    message_length = len(message)
    message_length = str(message_length).encode(encoding)
    message_length += b' ' * (header - len(message_length))
    connection.send(message_length)
    if encode:
        message = message.encode(encoding)
    connection.send(message)


def receive(connection: socket.socket, decode=True) -> str | bytes:
    """
    Receives a message from the given connection.
    :param connection: Connection to receive the message from.
    :param decode: Whether to decode the message or not.
    :return: The message that was received.
    """
    while True:
        try:
            message_length = int(connection.recv(header).decode(encoding))
            length_received = 0
            message = b''
            while length_received < message_length:
                message += connection.recv(message_length - length_received)
                length_received = len(message)
            if decode:
                message = message.decode(encoding)
            return message
        except ValueError:
            pass
