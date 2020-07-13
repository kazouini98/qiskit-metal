"""
Logging widget

Credits, based on:
    https://stackoverflow.com/questions/28655198/best-way-to-display-logs-in-pyqt
    and thanks to Phil Reinhold

Returns:
    [type] -- [description]
"""
import collections
import html
import logging
import random
from pathlib import Path

from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAction, QDockWidget, QTextEdit

from ....toolbox_python.utility_functions import clean_name, monkey_patch
from .... import Dict, __version__, config
from ...utility._handle_qt_messages import catch_exception_slot_pyqt

__all__ = ['QTextEditLogger', 'LogHandler_for_QTextLog']


class QTextEditLogger(QTextEdit):

    timestamp_len = 19
    _logo = 'metal_logo.png'

    def __init__(self, img_path='/', dock_window: QDockWidget = None):
        """
        Widget to handle logging. Based on QTextEdit, an advanced WYSIWYG viewer/editor
        supporting rich text formatting using HTML-style tags. It is optimized to handle
        large documents and to respond quickly to user input.

        Get as:
            gui.ui.log_text
        """
        super().__init__()

        self.img_path = img_path
        self.dock_window = dock_window

        # handles the loggers
        # dict for what loggers we track and if we should show or not
        self.tracked_loggers = Dict()
        self.handlers = Dict()
        self._actions = Dict()  # menu actions. Must be an ordered Dict!
        self._auto_scroll = True  # autoscroll to end or not
        self._show_timestamps = False
        self._level_name = ''

        # Props of the Widget
        self.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.text_format = QtGui.QTextCharFormat()
        self.text_format.setFontFamily('Consolas')

        self.logged_lines = collections.deque(
            [], config.GUI_CONFIG.logger.num_lines)

        self.setup_menu()

    def toggle_autoscroll(self, checked: bool):
        self._auto_scroll = bool(checked)

    def toggle_timestamps(self, checked: bool):
        self._show_timestamps = bool(checked)
        self.show_all_messages()

    def setup_menu(self):

        # Behaviour for menu: the widget displays its QWidget::actions() as context menu.
        # i.e., a local context menu
        self.setContextMenuPolicy(Qt.ActionsContextMenu)

        ###################
        # Click actions
        actions = self._actions

        actions.clear_log = QAction('&Clear log', self, triggered=self.clear)
        actions.print_tips = QAction(
            '&Show tips ', self, triggered=self.print_all_tips)

        actions.separator = QAction(self)
        actions.separator.setSeparator(True)

        ###################
        # Toggle actions
        self.actino_scroll_auto = QAction('&Autoscroll', self, checkable=True, checked=True,
                                          toggled=self.toggle_autoscroll)

        self.action_show_times = QAction('&Show timestamps', self, checkable=True, checked=False,
                                         toggled=self.toggle_timestamps)

        ###################
        # Filter level actions
        def make_trg(lvl):
            name = f'set_level_{lvl}'
            # self.set_level(lvl)
            setattr(self, name, lambda: self.set_level(lvl))
            func = getattr(self, name)
            return func
        actions.debug = QAction(
            'Set filter level:  Debug', self, triggered=make_trg(logging.DEBUG))
        actions.info = QAction('Set filter level:  Info',
                               self, triggered=make_trg(logging.INFO))
        actions.warning = QAction(
            'Set filter level:  Warning', self, triggered=make_trg(logging.WARNING))
        actions.error = QAction(
            'Set filter level:  Error', self, triggered=make_trg(logging.ERROR))

        actions.separator2 = QAction(self)
        actions.separator2.setSeparator(True)

        actions.loggers = QAction(
            'Show/hide messages for logger:', self, enabled=False)

        # Add actions to actin context menu
        self.addActions(list(actions.values()))

    def welcome_message(self):
        img_txt = ''

        # Logo
        img_path = Path(self.img_path)/self._logo
        if img_path.is_file():
            img_txt = f'<img src="{img_path}" height=80>'
        else:
            print(
                'WARNING: welcome_message could not locate img_path={img_path}')

        # Main message
        text = f'''<span class="INFO">{' '*self.timestamp_len}
        <br>
        <table border="0" width="100%" ID="tableLogo" style="margin: 0px;">
            <tr>
                <td align="center">
                    <h3 align="center"  style="text-align: center;">
                        Welcome to Qiskit Metal!
                    </h3>
                    v{__version__}
                </td>
                <td>  {img_txt} </td>
            </tr>
        </table>
        </span>
        <b>Tip: </b> {random.choice(config.GUI_CONFIG['tips'])}'''
        self.log_message(text, format_as_html=2)

    def print_all_tips(self):
        """Prints all availabel tips in the log window
        """
        for tip in config.GUI_CONFIG['tips']:
            self.log_message(
                f'''<br><span class="INFO">{' '*self.timestamp_len} \u2022 {tip} </span>''')

    def set_level(self, level: int):
        """Set level on all handelrs

        Arguments:
            level {[logging.level]} -- [eg.., logging.ERROR]
        """
        print(f'Setting level: {level}')
        self.set_window_title_level(level)
        for name, handler in self.handlers.items():
            handler.setLevel(level)

    def set_window_title_level(self, level: int):
        self._level_name = logging.getLevelName(level).lower()
        if self._level_name not in ['']:
            self.dock_window.setWindowTitle(
                f'Log  (filter >= {self._level_name})')
        else:
            self.dock_window.setWindowTitle(
                f'Log (right click log for options)')
        return self._level_name

    def add_logger(self, name: str, handler: logging.Handler):
        """
        Adds a logger to the widget.

            - adds `true bool`   to self.tracked_loggers for on/off to show
            - adds `the handler` in self.handlers
            - adds an action to the menu for the self.traceked_loggers

        For example, a logger handler is added with
            gui.logger.addHandler(self._log_handler)
        where
            _log_handler is LogHandler_for_QTextLog

        Arguments:
            name {string} -- Name of logger to be added
            handler {logging.Handler} -- handler
        """
        if name in self.tracked_loggers:
            return

        self.tracked_loggers[name] = True
        # can this be a problem if handler has multiple names?
        self.handlers[name] = handler

        #############################################
        # Monkey patch add function
        func_name = f'toggle_{clean_name(name)}'

        def toggle_show_log(self2, val: bool):
            """Toggle the value of the

            Arguments:
                self2 {QTextEdit} -- self
                val {bool} -- T/F

            Example:
                <bound method QTextEditLogger.add_logger.<locals>.toggle_show_log
                of <qiskit_metal._gui.widgets.log_widget.log_metal.QTextEditLogger object at 0x7fce3a500c18>>
            """
            self2.tracked_loggers[name] = bool(val)

        monkey_patch(self, toggle_show_log, func_name=func_name)
        #############################################

        # Add action
        action = QAction(f' - {name}', self,
                         checkable=True, checked=True,
                         triggered=getattr(self, func_name))
        self._actions[f'logger_{name}'] = action
        self.addAction(action)

        # style TODO: move
        self.document().setDefaultStyleSheet(config.GUI_CONFIG.logger.style)

        # is this the first logger we added
        if len(self.tracked_loggers) == 1:
            self.set_window_title_level(handler.level)

    def get_all_checked(self):
        res = []
        for name, isChecked in self.tracked_loggers.items():
            if isChecked:
                res += [name]
        return res

    def show_all_messages(self):
        """
        Clear and reprint all log lines, thus refreshing toggles for timestamp, etc.
        """
        self.clear()
        for name, record in self.logged_lines:
            if name in self.get_all_checked():
                self.log_message(record, not (name is 'Errors'))

    def log_message_to(self, name, record):
        self.logged_lines.append((name, record))
        if name in self.get_all_checked():
            self.log_message(record, not (name is 'Errors'))

    def log_message(self, message, format_as_html=True):
        """Do the actial logging

        Arguments:
            message {[type]} -- [description]

        Keyword Arguments:
            format_as_html {bool} -- [Do format as html or not] (default: {True})
        """
        # set the write positon
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertBlock()   # add a new block, which makes a new line

        # add message
        if format_as_html == True:  # pylint: disable=singleton-comparison

            if not self.action_show_times.isChecked():
                # remove the timestamp -- assumes that this has been formatted
                # with pre tag by LogHandler_for_QTextLog
                res = message.split('<pre>', 1)
                if len(res) == 2:
                    message = res[0] + '<pre>' + res[1][1+self.timestamp_len:]
                else:
                    pass  # print(f'Warning incorrect: {message}')

            cursor.insertHtml(message)

        elif format_as_html == 2:
            cursor.insertHtml(message)

        else:
            cursor.insertText(message, self.text_format)

        # make sure that the message is visible and scrolled ot
        if self.actino_scroll_auto.isChecked():
            self.moveCursor(QtGui.QTextCursor.End)
            self.moveCursor(QtGui.QTextCursor.StartOfLine)
        self.ensureCursorVisible()

    def remove_handlers(self, logger):
        """
        Call on clsoe window to remove handlers from the logger
        """
        for name, handler in self.handlers.items():
            if handler in logger.handlers:
                logger.handlers.remove(handler)


class LogHandler_for_QTextLog(logging.Handler):

    def __init__(self, name, parent,
                 log_qtextedit: QTextEditLogger,
                 logger: logging.Logger,
                 log_string=None):
        """
        Class to handle GUI logging.
        Handler instances dispatch logging events to specific destinations.
        For formatting
            https://docs.python.org/3/library/logging.html#logrecord-attributes
            _log_string = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')     # create formatter and add it to the handlers

        Arguments:
            name {[str]} -- [description]
            window {[QWidget]} -- [description]
        """
        super().__init__()

        self.name = name
        self.log_qtextedit = log_qtextedit
        self.setLevel(int(logger.level))
        self._logger = logger  # not sure if good idea to do this

        # Formatter
        if isinstance(log_string, str):
            self._log_string = log_string
        else:
            self._log_string = f'%(asctime).{QTextEditLogger.timestamp_len}s %(name)s: %(message)s [%(module)s.%(funcName)s]'
        self._log_formatter = logging.Formatter(self._log_string)
        self.setFormatter(self._log_formatter)

        # Add formatter to
        self.log_qtextedit.add_logger(name, self)

        self._logger.addHandler(self)  # ADD HANDLER!

    def emit(self, record):
        """
        Do whatever it takes to actually log the specified logging record.
        Converts the characters '&', '<' and '>' in string s to HTML-safe sequences.
        Used to display text that might contain such characters in HTML.
        Arguments:
            record {[LogRecord]} -- [description]
        """
        # print(record)
        #self.log_qtextedit.record = record
        #self.log_qtextedit.zz = self

        html_record = html.escape(self.format(record))
        html_log_message = '<span class="%s"><pre>%s</pre></span>' % (
            record.levelname, html_record)
        try:
            self.log_qtextedit.log_message_to(self.name, html_log_message)
        except RuntimeError as e:
            # trying to catch
            #  RuntimeError('wrapped C/C++ object of type QTextEditLogger has been deleted',)
            print(f'Logger issue: {e}')
            self._logger.handlers.remove(self)