# -*- coding: utf-8 -*-
"""
This module contains the class for the home screen of the app.
All the chats are created and managed from this screen.
"""

import time
import os
import uuid
import socket
import threading
import pickle
import main  # noqa
from dependencies.modules.communicator import send, receive  # noqa
from dependencies.modules.exceptionalthread import ThreadWithExc  # noqa
from dependencies.modules import pq_ntru  # noqa
from kivy.clock import mainthread, Clock
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.button import MDRectangleFlatButton

main_folder_path: str = os.path.join(os.path.expanduser(r'~\AppData\Local'), main.__PROJECT__)
data_folder_path: str = os.path.join(main_folder_path, 'data')
sizes = {
    (0, 5): 80,
    (5, 7): 90,
    (7, 9): 110,
    (9, 11): 125,
    (11, 13): 140,
    (13, 15): 160,
    (15, 17): 180,
    (17, 19): 195,
    (19, 21): 210,
    (21, 23): 230,
    (23, 25): 250,
}


class HomeScreen(Screen):
    """Main class for the home screen of the app."""

    SERVER: socket.socket = None
    ADDR: tuple = None
    SERVER_: socket.socket = None
    chat_screens: list = []
    listen_new_chats_thread: ThreadWithExc = None
    username: str = StringProperty('')
    _id: str = ''
    dialog: MDDialog = None

    def __delete__(self):
        if self.SERVER:
            send('3', self.SERVER)
            self.SERVER.close()
        if self.SERVER_:
            self.SERVER_.close()

        for chat in self.chat_screens:
            chat.chat_server.close()
            chat.listen_messages_thread.raiseExc(SystemExit)
            chat.save_chat()
            if chat.add_existing_chat_thread:
                chat.add_existing_chat_thread.raiseExc(SystemExit)
        try:
            self.listen_new_chats_thread.raiseExc(SystemExit)
        except (ValueError, AttributeError):
            pass

    def on_enter(self, *args):
        """Executed before the screen is entered."""
        if not self.SERVER_:
            # Create a new connection with the server to listen for new
            # chats.
            self.SERVER_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.SERVER_.connect((self.ADDR[0], 9090))

            # Receive the client username and id from the server.
            self.username, self._id = pickle.loads(receive(self.SERVER, False))

            self.listen_new_chats_thread = ThreadWithExc(target=self.listen_new_chats)
            self.listen_new_chats_thread.start()
        else:
            self.username = receive(self.SERVER)
            if self.dialog:
                self.dialog.text = f'Your current username is {self.username}.'

    def on_release_add_user(self):
        """
        Function to be executed when the add_user button is released.
        """

        if self.ids.add_user_button.icon == 'account-plus':
            self.ids.menu_title_label.text = 'Add User'
            self.ids.add_user_button.icon = 'chat'

            self.ids.menu_sm.current = 'AddUser'
        elif self.ids.add_user_button.icon == 'chat':
            self.ids.menu_title_label.text = 'Chats'
            self.ids.add_user_button.icon = 'account-plus'
            self.ids.menu_sm.current = 'Chats'

    def on_release_edit_username(self):
        """
        Function to be executed when the edit username button is
        released.
        """

        def on_release_change_button():
            """Function to be executed when the change button is released."""
            self.dialog.dismiss()
            send('2', self.SERVER)
            self.parent.current = 'UserName'

        def on_release_cancel_button():
            """Function to be executed when the cancel button is released."""
            self.dialog.dismiss()

        if not self.dialog:
            change_button = MDFlatButton(text='CHANGE')
            change_button.bind(on_release=lambda *args: on_release_change_button())

            cancel_button = MDFlatButton(text='CANCEL')
            cancel_button.bind(on_release=lambda *args: on_release_cancel_button())

            self.dialog = MDDialog(text=f'Your current username is {self.username}.',
                                   buttons=[cancel_button, change_button])

        self.dialog.open()

    @mainthread
    def on_release_user_chat_button(self, _id: str):
        """
        Function to be executed when a user chat button is released.
        """

        if not self.ids.chat_sm.current == _id:
            self.ids.chat_sm.current = _id

        else:
            self.ids.chat_sm.current = 'Display'

    def listen_new_chats(self):
        """Function to listen for new chats."""
        try:
            while True:
                # Wait for the server to send a port to connect to a new
                # chat.
                port = int(receive(self.SERVER_))

                if port:
                    # Connect to the chat server.
                    chat_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    chat_server.connect((self.ADDR[0], port))

                    # Add the chat to the GUI
                    self.add_chat(chat_server)
        except (SystemExit, ConnectionAbortedError):
            pass

    @mainthread
    def add_chat(self, chat_server: socket.socket):
        """Function to add a chat to the GUI."""
        other_user = pickle.loads(receive(chat_server, False))

        chat_started_user = receive(chat_server)
        if chat_started_user == other_user[2]:
            chat_started_user = other_user[0]
        else:
            chat_started_user = 'You'

        unread = pickle.loads(receive(chat_server, False))

        user_public_key = os.path.join(data_folder_path, f'{other_user[2]}')

        # Save the other user's public key.
        with open(f'{user_public_key}.pub', 'w') as file:
            file.write(other_user[1])

        # Create a button for the chat.
        user_chat_button = self.ids.Chats.add_user_button(other_user[0], other_user[2])
        user_chat_button.bind(on_release=lambda *args: self.on_release_user_chat_button(
            other_user[2]))
        if unread:
            user_chat_button.text_color = 'orange'

        chat = self.ChatScreen(name=other_user[2])
        chat.user_chat_button = user_chat_button
        chat.other_public_key = user_public_key
        chat.ids.username_label.text = other_user[0]
        chat.ids.chat_started_label.text = f'{chat_started_user} started the chat.'
        chat.self_id = self._id
        chat.other_user_id = other_user[2]
        chat.load_chat()

        # Check if the chat already exists.
        message = receive(chat_server)
        if message == '1':
            # Add the existing chat to the GUI.
            existing_chat = pickle.loads(receive(chat_server, False))
            chat.ids.message_input.hint_text = 'Loading chat...'
            chat.ids.message_input.disabled = True
            chat.ids.chat_scroll_view.do_scroll = False
            chat.add_existing_chat_thread = ThreadWithExc(target=chat.add_existing_chat,
                                                          args=(existing_chat,))
            chat.add_existing_chat_thread.start()
        chat.chat_server = chat_server

        self.ids.chat_sm.add_widget(chat)
        self.chat_screens.append(chat)

    class ChatScreen(Screen):

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.date: str = ''
            self.chat_server: socket.socket | None = None
            self.user_chat_button: MDRectangleFlatButton | None = None
            self.other_public_key: str = ''
            self.self_public_key: str = os.path.join(data_folder_path, f'{uuid.getnode()}')
            self.self_private_key: str = os.path.join(data_folder_path, f'{uuid.getnode()}')
            self.listen_messages_thread: ThreadWithExc = ThreadWithExc(target=self.listen_messages)
            self.listen_messages_thread.start()
            self.add_existing_chat_thread: ThreadWithExc | None = None
            # Since the messages are encrypted, the messages are
            # stored in a dictionary with the encrypted message as the
            # key and the decrypted message as the value.
            self.chat: dict = {}
            self.self_id: str = ''
            self.other_user_id: str = ''
            self.message_label: MDCard | None = None
            self.animation: Animation | None = None

            Window.bind(on_key_down=self.on_key_down)

        def on_enter(self, *args):
            """Executed when the screen is entered."""
            if self.user_chat_button.text_color == [1.0, 0.6470588235294118, 0.0, 1.0]:
                send('__170523Read170523__', self.chat_server)
            self.user_chat_button.text_color = 'white'
            self.ids.message_input.focus = True

        def on_key_down(self, *args):
            """Function executed whenever a keyboard key is pressed."""
            if args[1] == 13 and self.parent and self.parent.parent.parent.parent:
                self.send_message()

        def load_chat(self):
            """Function to load self-messages."""
            self_messages_path = os.path.join(data_folder_path,
                                              f'{self.other_user_id}.dat')
            if os.path.exists(self_messages_path):
                with open(self_messages_path, 'rb') as file:
                    self.chat = pickle.load(file)

        def save_chat(self):
            """Function to save self-messages."""
            self_messages_path = os.path.join(data_folder_path,
                                              f'{self.other_user_id}.dat')
            with open(self_messages_path, 'wb') as file:
                pickle.dump(self.chat, file)

        def add_existing_chat(self, chat):
            """
            Function to add an existing chat.
            This function is executed in a separate thread to
            prevent the GUI from freezing.
            """
            try:
                for message in chat:
                    if message[1] == self.other_user_id:
                        _message = self.decrypt_message(message[0])
                    else:
                        _message = message[0]
                    self.add_message(_message, message[2], message[1] == self.self_id,
                                     decrypted=True, animate=False)
                self.post_add_existing_chat()
                self.add_existing_chat_thread = None
            except SystemExit:
                pass

        @mainthread
        def post_add_existing_chat(self):
            """
            Function to be executed after adding an existing chat.
            """
            self.ids.message_input.disabled = False
            self.ids.message_input.focus = True
            self.ids.message_input.hint_text = 'Type a message'
            self.ids.chat_scroll_view.do_scroll = True

        def decrypt_message(self, message: str) -> str:
            """Function to decrypt a message."""
            try:
                message = self.chat[message]
            except KeyError:
                encrypted_message = message
                message = pq_ntru.decrypt(self.self_private_key, message)
                self.chat[encrypted_message] = message
            return message

        def listen_messages(self):
            """Function to listen for new messages."""
            try:
                while True:
                    if self.chat_server and not self.add_existing_chat_thread:
                        message = pickle.loads(receive(self.chat_server, False))
                        if not self.parent:
                            self.user_chat_button.text_color = 'orange'
                        else:
                            send('__170523Read170523__', self.chat_server)
                        self.add_message(message[0], message[2], message[1] == self.self_id)
            except SystemExit:
                pass

        def send_message(self):
            """Function to send a message."""

            def _send():
                """
                This function is executed in a separate thread to
                prevent the GUI from freezing as the message is
                encrypted which takes time.
                """
                message = self.ids.message_input.text
                if message:
                    self.add_message(message, time.strftime('%D::%H:%M'), True, False)
                    Clock.schedule_once(lambda *args: setattr(self.ids.message_input, 'text', ''))

                    encrypted_message = pq_ntru.encrypt(self.other_public_key, message)
                    self.chat[encrypted_message] = message

                    send(str(encrypted_message), self.chat_server)

            threading.Thread(target=_send).start()

        @mainthread
        def add_message(self, message: str, date_time: str, self_message: bool,
                        encrypted=True, decrypted=False, animate=True):
            """Function to add a message to the chat."""
            date_time = date_time.split('::')
            if not self.date or self.date != date_time[0]:
                self.date = date_time[0]
                date_label = self.DateLabel()
                date_label.ids.date_label.text = self.date
                self.ids.chat.add_widget(date_label)

            if self_message:
                message_label = self.SelfMessageLabel()
                if encrypted:
                    try:
                        message = self.chat[message]
                    except KeyError:
                        message = 'Unable to load message.'
                        message_label.ids.message_label.bold = False
                        message_label.ids.message_label.italic = True
            else:
                message_label = self.OtherMessageLabel()
                if not decrypted:
                    message = self.decrypt_message(message)

            message_label.add_text(message)
            message_label.ids.time_label.text = date_time[1]

            self.ids.chat.add_widget(message_label)
            self.ids.chat_scroll_view.scroll_to(message_label, animate=animate)
            if animate:
                if self.animation:
                    self.animation.stop(self.message_label)
                    self.message_label.opacity = 1
                self.message_label = message_label
                message_label.opacity = 0
                self.animation = Animation(opacity=1, duration=0.4)
                self.animation.start(message_label)
            self.ids.message_input.focus = True

        class SelfMessageLabel(BoxLayout):

            def add_text(self, text: str):
                """Function to add text to the message label."""
                self.ids.message_label.text = text
                for size in sizes:
                    if size[0] <= len(text) < size[1]:
                        self.width = sizes[size]
                        break
                else:
                    self.width = 260

        class OtherMessageLabel(MDCard):

            def add_text(self, text: str):
                """Function to add text to the message label."""
                self.ids.message_label.text = text
                for size in sizes:
                    if size[0] <= len(text) < size[1]:
                        self.width = sizes[size]
                        break
                else:
                    self.width = 260

        class DateLabel(MDCard):
            pass

    class UsersList(Screen):

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.users: list[HomeScreen.UsersList.UserButton] = []
            self.empty_list_label_text = ''

        class UserButton(MDRectangleFlatButton):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.id_: str = ''

        def add_user_button(self, username: str, _id: str) -> UserButton:
            """Function to add a user button to the list."""
            if not self.users:
                self.ids.users_list.clear_widgets()
            user_button = self.UserButton(text=username)
            user_button.id_ = _id
            self.ids.users_list.add_widget(user_button)
            self.users.append(user_button)
            return user_button

    class ChatsList(UsersList):

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.empty_list_label_text = 'There are no chats yet.'

    class AddUserList(Screen):

        def on_validate_username_input_text(self):
            """
            Function search for users with the username
            currently active"""
            username = self.ids.username_input.text
            if username:
                server = self.parent.parent.parent.parent.parent.SERVER
                send('1', server)
                send(username, server)
                users = pickle.loads(receive(server, False))
                if users:
                    for username, _id in users:
                        add_user_button = self.ids.users_list.add_user_button(username, _id)
                        add_user_button.bind(on_release=self.on_release_user_button)
                else:
                    self.ids.username_input.error = True

        def on_release_user_button(self, *args):
            """Function to be executed when a user button is released."""
            _id = args[0].id_
            if _id not in [chat.name for chat in
                           self.parent.parent.parent.parent.parent.chat_screens]:
                server = self.parent.parent.parent.parent.parent.SERVER
                send('0', server)
                send(_id, server)
                self.parent.parent.parent.parent.parent.on_release_add_user()
            else:
                self.parent.parent.parent.parent.parent.ids.chat_sm.current = _id
