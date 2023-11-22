# -*- coding: utf-8 -*-
"""
Main file for the client,
It handles all the connections with the server and creates the GUI.
Kivy is used for the GUI.
"""

__author__ = 'Oldmacintosh'
__version__ = 'v1.0.2'
__date__ = 'November 2023'
__PROJECT__ = 'PeerChat'
__DEBUG__ = False

import os
import uuid
import socket
import pickle
from dependencies.modules import pq_ntru

# Define all the paths
main_folder_path: str = os.path.join(os.path.expanduser(r'~\AppData\Local'), __PROJECT__)
data_folder_path: str = os.path.join(main_folder_path, 'data')
key_path = os.path.join(data_folder_path, str(uuid.getnode()))


# Since this function is utilized in multiprocessing,
# it is defined in this file. If it is defined in another file,
# Kivy is imported into that file in a new process, which results in
# the establishment of a new window.

# This file supports multiprocessing as it is designed that way
# to only import kivy in the main process.
def decrypt_messages(chat: list, other_user_id: str):
    """
    Decrypts all the new messages in the given chat and saves it in
    the given user's chat data so that it can be used later.
    This function can be run in a different process.
    :param chat: The chat to decrypt.
    :param other_user_id: The id of the other user in the chat.
    """
    chat_path = os.path.join(data_folder_path, f'{other_user_id}.dat')

    with open(chat_path, 'rb') as file:
        saved_chat = pickle.load(file)

    for message in chat:
        try:
            saved_chat[message[0]]
        except KeyError:
            if message[1] == other_user_id:
                saved_chat[message[0]] = pq_ntru.decrypt(key_path, message[0])

    with open(chat_path, 'wb') as file:
        pickle.dump(saved_chat, file)


if __name__ == '__main__':
    import sys
    import multiprocessing
    from tblib import pickling_support
    import pymsgbox

    multiprocessing.freeze_support()

    if not __DEBUG__:
        os.environ['KIVY_NO_CONSOLELOG'] = '1'
    try:
        from dependencies.modules.communicator import send, receive
        from dependencies.modules.exceptionalthread import ThreadWithExc
        from dependencies.modules import kivy_config
        from dependencies.modules.home_screen import HomeScreen
        from kivymd.app import MDApp
        from kivy.lang import Builder
        from kivy.core.window import Window
        from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
        from kivy.clock import Clock, ClockEvent, mainthread
        from kivy.uix.label import Label

        pickling_support.install()

        startup: bool = True

        ADDR: tuple[str, int] = (kivy_config.host, kivy_config.port)
        SERVER: socket.socket | None = None


        class EmptyScreen(Screen):
            """
            An empty screen to be used as a placeholder,
            transitions to the splash screen on startup.
            """

            def on_enter(self, *args):
                """
                Executed when the screen is entered.
                It adds the necessary screens and transitions to the
                splash screen.
                """

                for screen, screen_ids in zip([SplashScreen(), UserNameScreen(), HomeScreen()],
                                              kivy_config.__SCREENS__[1:]):
                    self.parent.ids[screen_ids] = screen
                    self.parent.add_widget(screen)

                Clock.schedule_once(lambda *arg: setattr(self.parent, 'current', 'Splash'))


        class SplashScreen(Screen):
            """
            The Application loads in to this screen first to
            connect to the server while playing the animation and
            transition in to the necessary screen.
            """

            loading_thread: ThreadWithExc | None = None

            def on_enter(self, *args):
                """Executed when the screen is entered."""
                if not __DEBUG__ and startup:
                    Clock.schedule_once(lambda *arg: self.animate(), 1)
                else:
                    Clock.schedule_once(lambda *arg: self.load_thread())

            def animate(self):
                """
                Types the name of the app and starts the loading.
                """
                self.ids.TypeWriter.typewrite(string='PeerChat', frequency=0.1,
                                              on_complete=self.load_thread)

            def load_thread(self):
                """Function to start loading in a thread."""
                app_instance.screen_manager.transition = SlideTransition(direction='up')
                self.loading_thread = ThreadWithExc(target=self.start_loading)
                Clock.schedule_once(lambda *arg: self.loading_thread.start())
                self.ids.loader.color = [1, 1, 1, 1]

            def start_loading(self):
                """
                Starts the actual loading of the app connecting to the
                server and then loading in to the necessary screen.
                """
                try:
                    global SERVER, startup
                    startup = False
                    # Create the public and private keys for the user
                    if not os.path.exists(fr'{key_path}.pub') or not os.path.exists(
                            fr'{key_path}.priv'):
                        pq_ntru.generate_keys(key_path, 'moderate', True)

                    SERVER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    SERVER.connect(ADDR)
                    # Set the keep alive options for the socket
                    SERVER.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    SERVER.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
                    SERVER.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)

                    send(str(uuid.getnode()), SERVER)

                    self.parent.ids.Home.SERVER = SERVER
                    self.parent.ids.Home.ADDR = ADDR

                    message = receive(SERVER)
                    if message == '0':
                        Clock.schedule_once(
                            lambda *arg: setattr(self.parent, 'current', 'UserName'))
                    else:
                        Clock.schedule_once(
                            lambda *arg: setattr(self.parent, 'current', 'Home'))
                except SystemExit:
                    pass
                except Exception as exception:
                    self.raise_exc(exception)

            @mainthread
            def raise_exc(self, exception: Exception):
                """
                Function to raise an exception in the main thread.
                """
                raise exception


        def on_validate_username():
            """
            Function to execute if the username is valid.
            It sends the public key to the server and then
            transitions to the home screen.
            """

            with open(f'{key_path}.pub') as file:
                public_key = file.read()

            send(public_key, SERVER)

            app_instance.screen_manager.transition = SlideTransition(direction='up')
            app_instance.screen_manager.current = 'Home'


        class UserNameScreen(Screen):
            """
            This screen is used to input the username from the user.
            """

            def validate_username(self):
                """Validates the username from the server."""
                username = self.ids.username_input.text
                # Check if the username is valid.
                if username and len(username) <= 20:
                    send(username, SERVER)
                    message = receive(SERVER)
                    if message == '0':
                        self.change_helper_text('This username is already taken.')
                        self.ids.username_input.error = True
                    else:
                        on_validate_username()
                        self.ids.username_input.text = ''

            @mainthread
            def change_helper_text(self, text: str):
                """Changes the helper text of the username input."""
                if not self.ids.username_input.helper_text == text:
                    self.ids.username_input.helper_text = ''
                    Clock.schedule_once(lambda *arg: setattr(
                        self.ids.username_input, 'helper_text', text), 0.1)


        class TypeWriter(Label):

            def typewrite(self, string, frequency, on_complete: callable = None):
                """
                Function to execute the typewriter effect in the label.
                :param string: The string to type.
                :param frequency: Time between each character.
                :param on_complete: Function to execute on completion.
                """
                typewriter = Clock.create_trigger(lambda *arg: typeit(), frequency)
                typewriter()

                def typeit():
                    """Adds the text to the label."""
                    nonlocal string
                    self.text += string[0]
                    string = string[1:]
                    if len(string) > 0:
                        typewriter()
                    else:
                        if on_complete:
                            Clock.schedule_once(lambda *arg: on_complete(), 1)


        class PeerChat(MDApp):

            class SM(ScreenManager):
                pass

            screen_manager: ScreenManager = None

            def build(self):
                self.theme_cls.theme_style = 'Dark'
                self.theme_cls.colors.update(kivy_config.colors)
                self.theme_cls.primary_palette = kivy_config.theme
                self.theme_cls.primary_hue = '700'
                self.theme_cls.colors['Dark']['Background'] = (
                    self.theme_cls.colors)[self.theme_cls.primary_palette]['500']
                for kv_file in os.listdir(r'dependencies\kv'):
                    Builder.load_file(os.path.join(r'dependencies\kv', kv_file))
                self.screen_manager = self.SM()
                return self.screen_manager


        app_instance = PeerChat()
        app_instance.run()

    except KeyboardInterrupt:
        pass
    except Exception as error:

        from kivy.logger import Logger

        pickle.dumps(sys.exc_info())
        Logger.exception('main: %s', str(error))
        if not __DEBUG__:
            pymsgbox.alert(
                text=f'''PeerChat has crashed due to an unexpected exception\nException"{
                error}"''', title='Error', button='OK')

    try:
        app_instance.screen_manager.ids.Home.__delete__()  # noqa
    except AttributeError:
        pass
    if Window:
        Window.close()
