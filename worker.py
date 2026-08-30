"""
Utilitaire technique pour exécuter un traitement long (tri, conversion...)
dans un thread séparé, afin que l'interface ne se fige pas pendant le
traitement de centaines/milliers de fichiers.

Ce fichier ne contient AUCUNE logique métier : c'est juste le câblage
PySide6 nécessaire pour brancher n'importe quelle fonction de traitement
sur l'interface (barre de progression, zone de log, bouton qui se
réactive à la fin). Chaque onglet l'utilise de la même façon.
"""

from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    """
    Exécute `fonction(log, progress, *args, **kwargs)` dans un thread séparé.

    - `fonction` doit accepter en premier et deuxième argument deux
      fonctions de rappel : `log(message)` et `progress(valeur, total)`.
    - Le signal `log_signal` transmet les messages à afficher dans l'interface.
    - Le signal `progress_signal` transmet (valeur, total) pour la barre de progression.
    - Le signal `termine_signal` transmet (succes: bool, message: str) à la fin.
    """

    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    termine_signal = Signal(bool, str)

    def __init__(self, fonction, *args, **kwargs):
        super().__init__()
        self.fonction = fonction
        self.args = args
        self.kwargs = kwargs

    def run(self):
        def log(message):
            self.log_signal.emit(str(message))

        def progress(valeur, total):
            self.progress_signal.emit(valeur, total)

        try:
            self.fonction(log, progress, *self.args, **self.kwargs)
            self.termine_signal.emit(True, "Terminé.")
        except Exception as e:
            self.termine_signal.emit(False, f"Erreur : {e}")
