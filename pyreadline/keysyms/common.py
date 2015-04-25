# -*- coding: utf-8 -*-
#*****************************************************************************
#       Copyright (C) 2003-2006 Gary Bishop.
#       Copyright (C) 2006  Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************
# table for translating virtual keys to X windows key symbols
from __future__ import print_function, unicode_literals, absolute_import

try:
    set
except NameError:
    from sets import Set as set  # @UnresolvedImport

from ctypes import windll

from .keysyms import code2sym_map
from ..unicode_helper import ensure_unicode

validkey =set(['cancel',      'backspace',    'tab',          'clear',
               'return',      'shift_l',      'control_l',    'alt_l',
               'pause',       'caps_lock',    'escape',       'space',
               'prior',       'next',         'end',          'home',
               'left',        'up',           'right',        'down',
               'select',      'print',        'execute',      'snapshot',
               'insert',      'delete',       'help',         'f1',
               'f2',          'f3',           'f4',           'f5',
               'f6',          'f7',           'f8',           'f9',
               'f10',         'f11',          'f12',          'f13',
               'f14',         'f15',          'f16',          'f17',
               'f18',         'f19',          'f20',          'f21',
               'f22',         'f23',          'f24',          'num_lock',
               'scroll_lock', 'vk_apps',      'vk_processkey','vk_attn',
               'vk_crsel',    'vk_exsel',     'vk_ereof',     'vk_play',
               'vk_zoom',     'vk_noname',    'vk_pa1',       'vk_oem_clear',
               'numpad0',     'numpad1',      'numpad2',      'numpad3',
               'numpad4',     'numpad5',      'numpad6',      'numpad7',
               'numpad8',     'numpad9',      'divide',       'multiply',
               'add',         'subtract',     'vk_decimal'])

escape_sequence_to_special_key = {"\\e[a" : "up", "\\e[b" : "down", "del" : "delete"}

VkKeyScan = windll.user32.VkKeyScanA

# XXX: Debugging only
def _trace_caller():
    try:
        raise RuntimeError()
    except RuntimeError as e:
        import traceback
        traceback.print_stack()


# Property factory
def _prop(attr, key, cleaner=None):
    def _get(self):
        d = getattr(self, attr)
        return d[key]

    def _set(self, val):
        d = getattr(self, attr)
        if cleaner is not None: val = cleaner(val)
        d[key] = val

    return property(_get, _set)



class ShiftState(object):
    # Properties
    shift   = _prop('_state', 'shift',   bool)
    control = _prop('_state', 'control', bool)
    meta    = _prop('_state', 'meta',    bool)


    # Initialization
    def __init__(self, **kwargs):
        self._state  = {}
        self.shift   = kwargs.get('shift',   False)
        self.control = kwargs.get('control', False)
        self.meta    = kwargs.get('meta',    False)


    @classmethod
    def from_code(cls, code):
        if code > 0xFF:
            raise ValueError("code out of range (must be <= 0xFF, got %x)" % code)
        self = cls()
        self.shift   = code & 0x01
        self.control = code & 0x02
        self.meta    = code & 0x04  # "Alt"
        return self

    def to_dict(self):
        return {'shift': self.shift, 'control': self.control, 'meta': self.meta }


    def __getattribute__(self, key):
        if key not in type(self).__dict__ and key not in ['shift', 'control', 'meta', '_state']:
            raise RuntimeError("Tried to get invalid attribute on ShiftState object: %s" % key)
        return object.__getattribute__(self, key)

    def __setattr__(self, key, val):
        if key not in type(self).__dict__ and key not in ['shift', 'control', 'meta', '_state']:
            raise RuntimeError("Tried to set invalid attribute on ShiftState object: %s" % key)
        return object.__setattr__(self, key, val)


class KeyPress(object):
    # Properties
    char    = _prop('_info', 'char')
    state   = _prop('_info', 'state')
    keyname = _prop('_info', 'keyname')


    # Initialization
    def __init__(self, **kwargs):
        self._info = {}
        char    = kwargs.get('char',    "")
        shift   = kwargs.get('shift',   False)
        control = kwargs.get('control', False)
        meta    = kwargs.get('meta',    False)
        keyname = kwargs.get('keyname', "")

        # char and keyname go straight into the _info dictionary
        self.char    = char
        self.keyname = keyname

        # shift, control, and meta build a ShiftState object which is put into _info
        self.state   = ShiftState(shift=shift, control=control, meta=meta)

        # Check if we need to force char to upper case, and do so if necessary
        if self.force_upper_char():
            self.char = self.char.upper()


    @classmethod
    def from_char(cls, **kwargs):
        char = kwargs.pop('char')
        # Initialize KeyPress object with "defaults" passed into from_char method
        self = cls(kwargs)

        # Translates a character to the corresponding virtual-key code and shift state for the
        #   current keyboard.
        # https://msdn.microsoft.com/en-us/library/windows/desktop/ms646329%28v=vs.85%29.aspx
        vk = VkKeyScan(ord(char))
        if vk & 0xffff == 0xffff:
            print('VkKeyScan("%s") = %x' % (char, vk))
            raise ValueError('bad key')

        # Split the character into upper (shift state) and lower (virtual-key code) bytes.
        ub   = (vk >> 8) & 0xFF
        lb   = (vk >> 0) & 0xFF
        # Get ShiftState overrides (if set, these will override defaults)
        sso  = ShiftState.from_code(ub)
        if sso.shift:   self.state.shift   = True
        if sso.control: self.state.control = True
        if sso.meta:    self.state.meta    = True
        # Update KeyPress object (self)'s char attribute
        self.char = chr(lb)
        # Return created object
        return self


    @classmethod
    def from_keydescr(cls, keydescr):
        self = cls()

        if len(keydescr) > 2 and keydescr[:1] == '"' and keydescr[-1:] == '"':
            keydescr = keydescr[1:-1]

        while 1:
            lkeyname = keydescr.lower()
            if lkeyname.startswith('control-'):
                self.state.control = True
                keydescr = keydescr[8:]
            elif lkeyname.startswith('ctrl-'):
                self.state.control = True
                keydescr = keydescr[5:]
            elif keydescr.lower().startswith('\\c-'):
                self.state.control = True
                keydescr = keydescr[3:]
            elif keydescr.lower().startswith('\\m-'):
                self.state.meta = True
                keydescr = keydescr[3:]
            elif keydescr in escape_sequence_to_special_key:
                keydescr = escape_sequence_to_special_key[keydescr]
            elif lkeyname.startswith('meta-'):
                self.state.meta = True
                keydescr = keydescr[5:]
            elif lkeyname.startswith('alt-'):
                self.state.meta = True
                keydescr = keydescr[4:]
            elif lkeyname.startswith('shift-'):
                self.state.shift = True
                keydescr = keydescr[6:]
            else:
                if len(keydescr) > 1:
                    if keydescr.strip().lower() in validkey:
                        self.keyname = keydescr.strip().lower()
                        self.char = ""
                    else:
                        raise IndexError("Not a valid key: '%s'"%keydescr)
                else:
                    self.char = keydescr
                return self


    @classmethod
    def from_char_state_code(cls, char, state, keycode):
        control = (state & (4+8)) != 0
        meta    = (state & (1+2)) != 0
        shift   = (state & 0x10)  != 0
        if control and not meta:  # Matches ctrl- chords should pass keycode as char
            char = chr(keycode)
        elif control and meta:    # Matches alt gr and should just pass on char
            control = False
            meta = False
        try:
            keyname=code2sym_map[keycode]
        except KeyError:
            keyname = ""
        out = cls(char=char, shift=shift, control=control, meta=meta, keyname=keyname)
        return out


    def __getattribute__(self, key):
        if key not in type(self).__dict__ and key not in ['char', 'state', 'keyname', '_info']:
            raise RuntimeError("Tried to get invalid attribute on KeyPress object: %s" % key)
        return object.__getattribute__(self, key)

    def __setattr__(self, key, val):
        if key not in ['char', 'state', 'keyname', '_info']:
            raise RuntimeError("Tried to set invalid attribute on KeyPress object: %s" % key)
        return object.__setattr__(self, key, val)


    def __repr__(self):
        def safe_str(s): return str(ensure_unicode(s))
        items = map(safe_str, self.to_tuple())
        return "(" + ','.join(items) + ")"


    def force_upper_char(self):
        state = self.state
        return (state.control or state.meta)  # Was (state.control or state.meta or state.shift)


    def to_dict(self):
        # Figure out what we're going to use as a description, and keep track of how we got it
        if self.keyname:
            desc_var = self.keyname
            desc_src = 'keyname'
        else:
            if self.force_upper_char():
                if self.char.upper() != self.char: _trace_caller()
                desc_var = self.char.upper()
                desc_src = 'char-upper'
            else:
                desc_var = self.char
                desc_src = 'char'

        # Get a dictionary from this object's state, and add the description keys
        d = self.state.to_dict()
        d['desc'] = desc_var
        d['dsrc'] = desc_src

        return d

    def to_tuple(self):
        #_trace_caller()
        d = self.to_dict()
        return (d['control'], d['meta'], d['shift'], d['desc'])


    def __eq__(self, other):
        if isinstance(other, KeyPress):
            s = self.to_dict()
            o = other.to_dict()
            # We don't care about the desc source
            s.pop('dsrc')
            o.pop('dsrc')
            return s == o
        else:
            return False




if __name__ == "__main__":
    from pyreadline.configuration import startup
