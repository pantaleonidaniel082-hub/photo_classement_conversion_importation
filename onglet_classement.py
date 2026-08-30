"""
Onglet : Classement des photos et vidéos par Année / Mois.

La logique métier (fonctions ci-dessous) est reprise TELLE QUELLE de
classement_photos_annee_mois.py. Les seuls changements :
    - plus de input() : les chemins viennent des champs de l'interface
    - plus de print() : on appelle log(message) à la place
    - la fonction principale reçoit en plus (log, progress), fournis
      automatiquement par worker.py
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

from PIL import Image
import exifread

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QTextEdit, QProgressBar, QMessageBox
)

from worker import Worker


EXTENSIONS_PHOTOS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff", ".webp"}
EXTENSIONS_VIDEOS = {".mov", ".mp4", ".m4v"}

MOIS = {
    1: "01 - Janvier", 2: "02 - Février", 3: "03 - Mars", 4: "04 - Avril",
    5: "05 - Mai", 6: "06 - Juin", 7: "07 - Juillet", 8: "08 - Août",
    9: "09 - Septembre", 10: "10 - Octobre", 11: "11 - Novembre", 12: "12 - Décembre",
}


# ============================================================
# LOGIQUE MÉTIER (reprise de classement_photos_annee_mois.py)
# ============================================================

def date_photo(fichier):
    """Date de prise de vue depuis les métadonnées EXIF (photos)."""
    try:
        with open(fichier, "rb") as f:
            tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal", details=False)
        date_exif = tags.get("EXIF DateTimeOriginal")
        if date_exif:
            return datetime.strptime(str(date_exif), "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return None


def date_video(fichier):
    """Date de création depuis les métadonnées vidéo (QuickTime, etc.)."""
    try:
        with Image.open(fichier) as img:
            if hasattr(img, "info"):
                info = img.info
                for cle in ["creation_time", "com.apple.quicktime.creationdate", "date"]:
                    if cle in info:
                        valeur = info[cle]
                        if isinstance(valeur, bytes):
                            valeur = valeur.decode("utf-8", errors="ignore")
                        for format_date in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d %H:%M:%S"]:
                            try:
                                return datetime.strptime(str(valeur)[:19], format_date)
                            except ValueError:
                                pass
    except Exception:
        pass
    return None


def date_fichier(fichier):
    """Dernier recours : date de création du fichier sur le disque."""
    try:
        timestamp = os.path.getctime(fichier)
        return datetime.fromtimestamp(timestamp)
    except Exception:
        return None


def obtenir_date(fichier):
    extension = fichier.suffix.lower()

    if extension in EXTENSIONS_PHOTOS:
        date = date_photo(fichier)
        if date:
            return date
    elif extension in EXTENSIONS_VIDEOS:
        date = date_video(fichier)
        if date:
            return date

    return date_fichier(fichier)


def nom_unique(destination):
    """Évite d'écraser un fichier existant en ajoutant (1), (2)..."""
    if not destination.exists():
        return destination

    compteur = 1
    while True:
        nouveau_nom = destination.stem + f" ({compteur})" + destination.suffix
        nouveau_chemin = destination.parent / nouveau_nom
        if not nouveau_chemin.exists():
            return nouveau_chemin
        compteur += 1


def classer_fichiers(log, progress, source, destination):
    """
    Fonction principale, lancée dans un thread séparé (voir worker.py).
    `log(message)` affiche une ligne dans le journal de l'interface.
    `progress(valeur, total)` met à jour la barre de progression.
    """
    source = Path(source)
    destination = Path(destination)

    if not source.exists():
        log("ERREUR : le dossier source n'existe pas.")
        return

    destination.mkdir(parents=True, exist_ok=True)

    fichiers = [
        f for f in source.rglob("*")
        if f.is_file() and f.suffix.lower() in (EXTENSIONS_PHOTOS | EXTENSIONS_VIDEOS)
    ]

    total = len(fichiers)
    log(f"Fichiers trouvés : {total}")
    log("")

    compteur = 0
    erreurs = 0

    for i, fichier in enumerate(fichiers, start=1):
        try:
            date = obtenir_date(fichier)

            if date:
                dossier_destination = destination / str(date.year) / MOIS[date.month]
            else:
                dossier_destination = destination / "Date inconnue"

            dossier_destination.mkdir(parents=True, exist_ok=True)

            chemin_dest = nom_unique(dossier_destination / fichier.name)
            shutil.copy2(fichier, chemin_dest)

            compteur += 1
            log(f"[{i}/{total}] {fichier.name} → {dossier_destination}")

        except Exception as e:
            erreurs += 1
            log(f"ERREUR : {fichier.name} — {e}")

        progress(i, total)

    log("")
    log("=" * 50)
    log("TERMINÉ")
    log(f"Fichiers copiés : {compteur}")
    log(f"Erreurs        : {erreurs}")
    log(f"Destination : {destination}")


# ============================================================
# INTERFACE
# ============================================================

class OngletClassement(QWidget):

    def __init__(self):
        super().__init__()
        self.worker = None
        self._construire_interface()

    def _construire_interface(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Dossier source (photos/vidéos à trier) :"))
        ligne_source = QHBoxLayout()
        self.champ_source = QLineEdit()
        bouton_source = QPushButton("Parcourir...")
        bouton_source.clicked.connect(self._choisir_source)
        ligne_source.addWidget(self.champ_source)
        ligne_source.addWidget(bouton_source)
        layout.addLayout(ligne_source)

        layout.addWidget(QLabel("Dossier de destination :"))
        ligne_dest = QHBoxLayout()
        self.champ_destination = QLineEdit()
        bouton_dest = QPushButton("Parcourir...")
        bouton_dest.clicked.connect(self._choisir_destination)
        ligne_dest.addWidget(self.champ_destination)
        ligne_dest.addWidget(bouton_dest)
        layout.addLayout(ligne_dest)

        self.bouton_lancer = QPushButton("Lancer le classement")
        self.bouton_lancer.setObjectName("boutonPrincipal")
        self.bouton_lancer.clicked.connect(self._lancer)
        layout.addWidget(self.bouton_lancer)

        self.barre_progression = QProgressBar()
        layout.addWidget(self.barre_progression)

        layout.addWidget(QLabel("Journal :"))
        self.zone_log = QTextEdit()
        self.zone_log.setReadOnly(True)
        layout.addWidget(self.zone_log)

    def _choisir_source(self):
        dossier = QFileDialog.getExistingDirectory(self, "Choisir le dossier source")
        if dossier:
            self.champ_source.setText(dossier)

    def _choisir_destination(self):
        dossier = QFileDialog.getExistingDirectory(self, "Choisir le dossier de destination")
        if dossier:
            self.champ_destination.setText(dossier)

    def _lancer(self):
        source = self.champ_source.text().strip()
        destination = self.champ_destination.text().strip()

        if not source or not destination:
            QMessageBox.warning(
                self, "Champs manquants",
                "Merci de choisir un dossier source et un dossier de destination."
            )
            return

        self.zone_log.clear()
        self.barre_progression.setValue(0)
        self.bouton_lancer.setEnabled(False)

        self.worker = Worker(classer_fichiers, source, destination)
        self.worker.log_signal.connect(self._ajouter_log)
        self.worker.progress_signal.connect(self._maj_progression)
        self.worker.termine_signal.connect(self._fin_traitement)
        self.worker.start()

    def _ajouter_log(self, message):
        self.zone_log.append(message)

    def _maj_progression(self, valeur, total):
        if total > 0:
            self.barre_progression.setMaximum(total)
            self.barre_progression.setValue(valeur)

    def _fin_traitement(self, succes, message):
        self.bouton_lancer.setEnabled(True)
        if succes:
            QMessageBox.information(self, "Terminé", "Le classement est terminé. Voir le journal pour le détail.")
        else:
            QMessageBox.critical(self, "Erreur", message)
