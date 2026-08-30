"""
Feuille de style (QSS) pour l'ensemble de l'application — thème sombre.

Palette d'accent (inchangée) :
    Menthe    #76E1AE  (118, 225, 174)
    Vert sauge#519B78  ( 81, 155, 120)
    Groseille #A32E6D  (163,  46, 109)
    Mauve     #8D5AA3  (141,  90, 163)

Fond gris-vert foncé, avec les couleurs d'accent qui ressortent dessus.

Ce fichier ne contient que de la présentation (aucune logique métier).
Il est appliqué une seule fois, globalement, depuis main.py.
"""

STYLE_SHEET = """
QWidget {
    background-color: #1B2420;
    color: #E7F0EA;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 10.5pt;
}

QLabel {
    color: #DCE9E1;
}

/* ---------- Onglets ---------- */

QTabWidget::pane {
    border: 1px solid #34473D;
    border-radius: 8px;
    background-color: #212C27;
    top: -1px;
}

QTabBar::tab {
    background-color: #26332C;
    color: #B9CBC0;
    padding: 10px 22px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}

QTabBar::tab:hover {
    background-color: #33463C;
    color: #E7F0EA;
}

QTabBar::tab:selected {
    background-color: #A32E6D;
    color: #FFFFFF;
}

/* ---------- Champs de saisie ---------- */

QLineEdit {
    background-color: #212C27;
    color: #E7F0EA;
    border: 1px solid #3B4F44;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #519B78;
}

QLineEdit:focus {
    border: 1px solid #B07AC4;
}

QTextEdit {
    background-color: #171F1B;
    color: #D6E5DC;
    border: 1px solid #3B4F44;
    border-radius: 6px;
    padding: 6px;
    font-family: Consolas, "Courier New", monospace;
    font-size: 9.5pt;
}

QCheckBox {
    spacing: 8px;
    color: #DCE9E1;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #6FAE8C;
    border-radius: 4px;
    background-color: #212C27;
}

QCheckBox::indicator:checked {
    background-color: #519B78;
    border: 1px solid #6FAE8C;
}

/* ---------- Boutons secondaires (ex: "Parcourir...") ---------- */

QPushButton {
    background-color: #212C27;
    color: #DCE9E1;
    border: 1px solid #6FAE8C;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #2C3B33;
}

QPushButton:pressed {
    background-color: #34473D;
}

QPushButton:disabled {
    color: #5C6F65;
    border: 1px solid #34473D;
    background-color: #1E2823;
}

/* ---------- Bouton principal ("Lancer...") ---------- */

QPushButton#boutonPrincipal {
    background-color: #519B78;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 11px 18px;
    font-weight: 700;
    font-size: 11pt;
}

QPushButton#boutonPrincipal:hover {
    background-color: #5FB088;
}

QPushButton#boutonPrincipal:pressed {
    background-color: #458569;
}

QPushButton#boutonPrincipal:disabled {
    background-color: #34473D;
    color: #79907F;
}

/* ---------- Barre de progression ---------- */

QProgressBar {
    border: 1px solid #3B4F44;
    border-radius: 6px;
    background-color: #171F1B;
    text-align: center;
    color: #E7F0EA;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #76E1AE;
    border-radius: 5px;
}

/* ---------- Divers ---------- */

QMessageBox {
    background-color: #212C27;
}

QScrollBar:vertical {
    background: #171F1B;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #3B4F44;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #519B78;
}
"""
