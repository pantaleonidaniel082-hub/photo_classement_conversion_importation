"""
Application de gestion de photos — fenêtre principale.

Assemble les différents onglets. Chaque onglet correspond à un des
scripts originaux et reste indépendant des autres : on peut en ajouter
un nouveau sans toucher au reste.
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel
)
from PySide6.QtCore import Qt

from onglet_classement import OngletClassement
from onglet_conversion import OngletConversion
from onglet_iphone import OngletIphone
from style import STYLE_SHEET


def onglet_a_venir(nom):
    """Placeholder pour les onglets pas encore construits (étapes suivantes)."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    label = QLabel(f"{nom}\n\n(à construire à l'étape suivante)")
    label.setAlignment(Qt.AlignCenter)
    layout.addWidget(label)
    return widget


class FenetrePrincipale(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestionnaire de photos")
        self.resize(800, 600)

        onglets = QTabWidget()
        onglets.addTab(OngletClassement(), "Classement par date")
        onglets.addTab(OngletConversion(), "Conversion")
        onglets.addTab(OngletIphone(), "Import iPhone")

        self.setCentralWidget(onglets)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)
    fenetre = FenetrePrincipale()
    fenetre.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
