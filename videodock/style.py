STYLE = """
* { font-family: 'Segoe UI'; font-size: 13px; color: #e4e9f2; }
QMainWindow, QWidget#workspace, QStackedWidget, QScrollArea { background: #101319; }
QWidget#sidebar { background: #151a22; border-right: 1px solid #262d38; }
QFrame#card { background: #191f29; border: 1px solid #2c3441; border-radius: 16px; }
QFrame#preview { background: #121820; border: 1px solid #2c3441; border-radius: 12px; }
QLabel { background: transparent; border: none; }
QLabel#brand { font-size: 21px; font-weight: 700; color: #f5f7fb; }
QLabel#eyebrow { font-size: 10px; font-weight: 700; color: #7f91a9; letter-spacing: 2px; }
QLabel#heading { font-size: 29px; font-weight: 700; color: #f3f6fb; }
QLabel#cardTitle { font-size: 15px; font-weight: 600; color: #f1f4fa; }
QLabel#muted { color: #94a3b8; font-size: 12px; }
QLabel#small { color: #8a99ae; font-size: 11px; }
QLabel#badge { color: #75e5b7; background: #203b34; border-radius: 9px; padding: 5px 10px; font-size: 11px; font-weight: 600; }
QLabel#status { color: #c5d1e1; }
QLabel#error { color: #ffa8a8; }
QLabel#success { color: #75e5b7; }
QLineEdit { background: #10161e; border: 1px solid #354152; border-radius: 9px; padding: 11px 12px; selection-background-color: #315b4c; }
QLineEdit:focus { border: 1px solid #69d9ac; background: #131c23; }
QLineEdit:disabled { color: #667387; border-color: #29313d; }
QPushButton { background: #252e3c; border: 1px solid #394659; border-radius: 9px; padding: 10px 15px; font-weight: 600; }
QPushButton:hover { background: #303e51; border-color: #61748c; }
QPushButton:pressed { background: #1e2835; }
QPushButton:disabled { background: #202630; border-color: #2c3541; color: #657286; }
QPushButton#primary { background: #77e0b5; color: #10261d; border: none; font-size: 14px; font-weight: 700; padding: 13px 23px; }
QPushButton#primary:hover { background: #97f0cc; }
QPushButton#primary:pressed { background: #58c397; }
QPushButton#primary:disabled { background: #2c5145; color: #739a8b; }
QPushButton#nav { text-align: left; border: none; color: #9baac0; background: transparent; padding: 13px 15px; }
QPushButton#nav:hover { background: #202936; color: #f0f5fc; }
QPushButton#nav:checked { background: #24392f; color: #8dedc2; }
QPushButton#segment { background: #111821; color: #94a3b8; border-color: #303b4b; padding: 11px 14px; }
QPushButton#segment:checked { background: #283e36; border-color: #6dccaa; color: #a3f3d0; }
QPushButton#textButton { border: none; color: #8ee8c1; background: transparent; padding: 4px; font-size: 12px; }
QComboBox { background: #10161e; border: 1px solid #354152; border-radius: 9px; padding: 11px 12px; padding-right: 26px; }
QComboBox:focus { border-color: #69d9ac; }
QComboBox:disabled { color: #667387; border-color: #29313d; }
QComboBox::drop-down { border: none; width: 25px; }
QComboBox::down-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #95a9bf; width: 0px; height: 0px; }
QComboBox QAbstractItemView { background: #202a37; color: #e4e9f2; selection-background-color: #365648; border: 1px solid #46566b; padding: 5px; }
QCheckBox { spacing: 9px; color: #dce5f1; }
QCheckBox::indicator { width: 19px; height: 19px; border: 1px solid #526079; border-radius: 5px; background: #111821; }
QCheckBox::indicator:checked { background: #77e0b5; border-color: #77e0b5; image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png); }
QProgressBar { background: #10161e; border: none; border-radius: 4px; min-height: 7px; max-height: 7px; color: transparent; }
QProgressBar::chunk { background: #77e0b5; border-radius: 4px; }
QScrollArea { border: none; }
QScrollBar:vertical { background: #101319; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #384252; border-radius: 4px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QTextEdit { background: #10161e; color: #97a8bd; border: 1px solid #344052; border-radius: 8px; font-family: Consolas; font-size: 11px; padding: 7px; }
QToolTip { color: #e4e9f2; background: #2a3545; border: 1px solid #475970; padding: 6px; }
"""
