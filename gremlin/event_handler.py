# -*- coding: utf-8; -*-

# Copyright (C) 2015 Lionel Ott
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import enum
import inspect
import logging
import time
from threading import Thread

import pyHook
from PyQt5 import QtCore
import pythoncom
import sdl2
import sdl2.ext

from gremlin.util import SingletonDecorator
from gremlin import error, macro, util


class InputType(enum.Enum):

    """Enumeration of the possible input types."""

    Keyboard = 1
    JoystickAxis = 2
    JoystickButton = 3
    JoystickHat = 4
    Count = 5


class Event(object):

    """Represents a single event captured by the system.

    An event can originate from the keyboard or joystick which is
    indicated by the EventType value. The value of the event has to
    be interpreted based on the type of the event.

    Keyboard and JoystickButton events have a simple True / False
    value stored in is_pressed indicating whether or not the key has
    been pressed. For JoystickAxis the value indicates the axis value
    in the range [-1, 1] stored in the value field. JoystickHat events
    represent the hat position as a unit tuple (x, y) representing
    deflection in cartesian coordinates in the value field.

    The extended field is used for Keyboard events only to indicate
    whether or not the key's scan code is extended one.
    """

    ShiftEventId = 36
    ShiftDeviceId = 0
    ShiftSystemId = 32
    ShiftIdentifier = 40

    def __init__(self, event_type, identifier, device_id, system_id, value=None, is_pressed=None):
        """Creates a new Event object.

        :param event_type the type of the event, one of the EventType values
        :param identifier the identifier of the event source
        :param device_id the identifier of the device which created the event
        :param system_id the index of the device in the system
        :param value the value of a joystick axis or hat
        :param is_pressed boolean flag indicating if a button or key
            is pressed
        """
        self.event_type = event_type
        self.identifier = identifier
        self.device_id = device_id
        self.system_id = system_id
        self.is_pressed = is_pressed
        self.value = value

    def clone(self):
        """Returns a clone of the event.

        :return cloned copy of this event
        """
        return Event(
            self.event_type,
            self.identifier,
            self.device_id,
            self.system_id,
            self.value,
            self.is_pressed
        )

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        """Computes the hash value of this event.

        The hash is comprised of the events type, identifier of the
        event source and the id of the event device.

        :return integer hash value of this event
        """
        hash_val = 0
        if self.event_type == InputType.Keyboard:
            extended_val = 1 << 8 if self.identifier[1] else 0
            hash_val += (extended_val + int(self.identifier[0])) << Event.ShiftIdentifier
        else:
            hash_val += self.identifier << Event.ShiftIdentifier
        hash_val += self.event_type.value << Event.ShiftEventId
        if util.g_duplicate_devices:
            hash_val += self.system_id << Event.ShiftSystemId
        hash_val += self.device_id << Event.ShiftDeviceId

        return hash_val

    @staticmethod
    def from_key(key):
        """Creates an event object corresponding to the provided key.

        :param key the Key object from which to create the Event
        :return Event object corresponding to the provided key
        """
        assert isinstance(key, macro.Keys.Key)
        return Event(
            event_type=InputType.Keyboard,
            identifier=(key.scan_code, key.is_extended),
            device_id=0,
            system_id=0
        )


@SingletonDecorator
class EventListener(QtCore.QObject):

    """Listens for keyboard and joystick events and publishes them
    via QT's signal/slot interface.
    """

    # Signal emitted when keyboard events are received
    keyboard_event = QtCore.pyqtSignal(Event)
    # Signal emitted when joystick events are received
    joystick_event = QtCore.pyqtSignal(Event)

    def __init__(self):
        """Creates a new instance."""
        QtCore.QObject.__init__(self)
        self._hook_manager = pyHook.HookManager()
        self._hook_manager.KeyAll = self._keyboard_handler
        self._hook_manager.HookKeyboard()
        self._joysticks = {}
        self._joystick_guid_map = {}
        self._running = True
        self._keyboard_state = {}

        self._init_joysticks()
        Thread(target=self._run).start()

    def terminate(self):
        """Stops the loop from running."""
        self._running = False

    def _run(self):
        """Starts the event loop."""
        while self._running:
            # Process keyboard events
            pythoncom.PumpWaitingMessages()
            # Process joystick events
            for event in sdl2.ext.get_events():
                self._joystick_handler(event)
            time.sleep(0.001)

    def _keyboard_handler(self, event):
        """Callback for keyboard events.

        The handler converts the event data into a signal which is then
        emitted.

        :param event the keyboard event
        """
        # Ignore events we created via the macro system
        if event.Injected == 0:
            key_id = (event.ScanCode, event.Extended)
            is_pressed = not (event.Message & 257) == 257
            is_repeat = self._keyboard_state.get(key_id, False) and is_pressed
            # Only emit an event if they key is pressed for the first
            # time or released but not when it's being held down
            if not is_repeat:
                self._keyboard_state[key_id] = is_pressed
                self.keyboard_event.emit(Event(
                    event_type=InputType.Keyboard,
                    device_id=0,
                    system_id=0,
                    identifier=key_id,
                    is_pressed=is_pressed,
                ))
        # Allow the windows event to propagate further
        return True

    def _joystick_handler(self, event):
        """Callback for joystick events.

        The handler converts the event data into a signal which is then
        emitted.

        :param event the joystick event
        """
        if event.type == sdl2.SDL_JOYAXISMOTION:
            self.joystick_event.emit(Event(
                event_type=InputType.JoystickAxis,
                device_id=self._joystick_guid_map[event.jaxis.which],
                system_id=event.jaxis.which,
                identifier=event.jaxis.axis + 1,
                value=event.jaxis.value / float(32768)
            ))
        elif event.type in [sdl2.SDL_JOYBUTTONDOWN, sdl2.SDL_JOYBUTTONUP]:
            self.joystick_event.emit(Event(
                event_type=InputType.JoystickButton,
                device_id=self._joystick_guid_map[event.jbutton.which],
                system_id=event.jbutton.which,
                identifier=event.jbutton.button + 1,
                is_pressed=event.jbutton.state == 1
            ))
        elif event.type == sdl2.SDL_JOYHATMOTION:
            self.joystick_event.emit(Event(
                event_type=InputType.JoystickHat,
                device_id=self._joystick_guid_map[event.jhat.which],
                system_id=event.jhat.which,
                identifier=event.jhat.hat + 1,
                value=util.convert_sdl_hat(event.jhat.value)
            ))

    def _init_joysticks(self):
        """Initializes joystick devices."""
        for i in range(sdl2.joystick.SDL_NumJoysticks()):
            joy = sdl2.SDL_JoystickOpen(i)
            guid = util.guid_to_number(sdl2.SDL_JoystickGetGUID(joy).data)
            self._joysticks[guid] = joy
            self._joystick_guid_map[sdl2.SDL_JoystickInstanceID(joy)] = guid


@SingletonDecorator
class EventHandler(QtCore.QObject):

    """Listens to the inputs from multiple different input devices."""

    # Signal emitted when the mode is changed
    mode_changed = QtCore.pyqtSignal(str)
    # Signal emitted when the application is pause / resumed
    is_active = QtCore.pyqtSignal(bool)

    def __init__(self):
        """Creates a new instance."""
        QtCore.QObject.__init__(self)
        self.process_callbacks = True
        self.plugins = []
        self.callbacks = {}
        self._active_mode = "global"
        self._previous_mode = "global"

    @property
    def active_mode(self):
        return self._active_mode

    @property
    def previous_mode(self):
        return self._previous_mode

    def add_plugin(self, plugin):
        """Adds a new plugin to be attached to event callbacks.

        :param plugin the plugin to add
        """
        # Do not add the same type of plugin multiple times
        for entry in self.plugins:
            if type(entry) == type(plugin):
                return
        self.plugins.append(plugin)

    def add_callback(self, device_id, mode, event, callback, permanent=False):
        """Installs the provided callback for the given event.

        :param device_id the id of the device the callback is
            associated with
        :param mode the mode the callback belongs to
        :param event the event for which to install the callback
        :param callback the callback function to link to the provided
            event
        :param permanent if True the callback is always active even
            if the system is paused
        """
        if device_id not in self.callbacks:
            self.callbacks[device_id] = {}
        if mode not in self.callbacks[device_id]:
            self.callbacks[device_id][mode] = {}
        if event not in self.callbacks[device_id][mode]:
            self.callbacks[device_id][mode][event] = []
        self.callbacks[device_id][mode][event].append((
            self._install_plugins(callback),
            permanent
        ))

    def change_mode(self, new_mode):
        """Changes the currently active mode.

        :param new_mode the new mode to use
        """
        mode_exists = False
        for device in self.callbacks.values():
            if new_mode in device:
                mode_exists = True
        if not mode_exists:
            logging.error("The mode \"{}\" does not exist or has no"
                          " associated callbacks".format(new_mode))

        if mode_exists:
            self._previous_mode = self._active_mode
            self._active_mode = new_mode
            self.mode_changed.emit(self._active_mode)

    def resume(self):
        """Resumes the processing of callbacks."""
        self.process_callbacks = True
        self.is_active.emit(self.process_callbacks)

    def pause(self):
        """Stops the processing of callbacks."""
        self.process_callbacks = False
        self.is_active.emit(self.process_callbacks)

    def clear(self):
        """Removes all attached callbacks."""
        self.callbacks = {}

    @QtCore.pyqtSlot(Event)
    def process_event(self, event):
        """Processes a single event by passing it to all callbacks
        registered for this event.

        :param event the event to process
        """
        for cb in self._matching_callbacks(event):
            try:
                cb(event)
            except error.VJoyError as e:
                util.display_error(str(e))
                logging.exception("VJoy related error: {}".format(e))
                self.pause()

    def _matching_callbacks(self, event):
        """Returns the list of callbacks to execute in response to
        the provided event.

        :param event the event for which to search the matching
            callbacks
        :return a list of all callbacks registered and valid for the
            given event
        """
        callback_list = []
        # Obtain callbacks matching the event
        if event.device_id in self.callbacks:
            callback_list = self.callbacks[event.device_id].get(
                self._active_mode, {}
            ).get(event, [])
            if len(callback_list) == 0:
                callback_list = self.callbacks[event.device_id].get(
                    "global", {}
                ).get(event, [])
        # Filter events when the system is paused
        if not self.process_callbacks:
            return [c[0] for c in callback_list if c[1]]
        else:
            return [c[0] for c in callback_list]

    def _install_plugins(self, callback):
        """Installs the current plugins into the given callback.

        :param callback the callback function to install the plugins
            into
        :return new callback with plugins installed
        """
        signature = inspect.signature(callback)
        new_callback = self.plugins[0].install(callback, signature)
        for plugin in self.plugins[1:]:
            new_callback = plugin.install(new_callback, signature)
        return new_callback