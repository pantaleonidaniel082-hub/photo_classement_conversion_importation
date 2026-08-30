"""
Onglet : Copie + conversion des photos en JPG.

La logique métier (fonctions ci-dessous) est reprise TELLE QUELLE de
copier_et_convertir_photos_en_jpg.py. Les seuls changements :
    - plus de input() : les chemins viennent des champs de l'interface
    - plus de print() : on appelle log(message) à la place
    - la fonction principale reçoit en plus (log, progress), fournis
      automatiquement par worker.py
"""

import io
import shutil
from pathlib import Path

from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()  # permet à Pillow de lire les .HEIC
    HEIC_DISPONIBLE = True
except ImportError:
    HEIC_DISPONIBLE = False

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QTextEdit, QProgressBar, QMessageBox
)

from worker import Worker


PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".heic", ".heif", ".png", ".tiff", ".bmp")
VIDEO_EXTENSIONS = (".mov", ".mp4")


# ============================================================
# LOGIQUE MÉTIER (reprise de copier_et_convertir_photos_en_jpg.py)
# ============================================================

def convert_to_jpg(raw_data: bytes) -> bytes:
    """Convertit des données image (HEIC, PNG, ...) en JPG, renvoie les bytes JPG."""
    with Image.open(io.BytesIO(raw_data)) as img:
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=92, exif=img.info.get("exif", b""))
        return buffer.getvalue()


def unique_destination(dest_folder: Path, filename: str) -> Path:
    """Renvoie un chemin de destination qui n'écrase rien (ajoute _1, _2... si besoin)."""
    dest_path = dest_folder / filename
    if not dest_path.exists():
        return dest_path

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        candidate = dest_folder / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def copier_fichiers(log, progress, source, destination):
    """
    Fonction principale, lancée dans un thread séparé (voir worker.py).
    `log(message)` affiche une ligne dans le journal de l'interface.
    `progress(valeur, total)` met à jour la barre de progression.
    """
    source_dir = Path(source)
    dest_dir = Path(destination)
    dest_dir.mkdir(parents=True, exist_ok=True)

    fichiers = [
        p for p in source_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in PHOTO_EXTENSIONS + VIDEO_EXTENSIONS
    ]

    total = len(fichiers)
    log(f"{total} fichier(s) trouvé(s) dans {source_dir}")
    log("")

    if total == 0:
        return

    copies = 0
    ignores = 0
    erreurs = 0

    for i, fichier in enumerate(fichiers, start=1):
        ext = fichier.suffix.lower()
        est_photo = ext in PHOTO_EXTENSIONS
        est_heic = ext in (".heic", ".heif")

        if est_heic and not HEIC_DISPONIBLE:
            log(f"[{i}/{total}] IGNORÉ (module HEIC absent) : {fichier.name}")
            erreurs += 1
            progress(i, total)
            continue

        nom_dest = f"{fichier.stem}.jpg" if est_photo else fichier.name
        chemin_dest = dest_dir / nom_dest

        if chemin_dest.exists():
            ignores += 1
            progress(i, total)
            continue

        try:
            if est_photo:
                data = fichier.read_bytes()
                data = convert_to_jpg(data)
                chemin_dest.write_bytes(data)
            else:
                shutil.copy2(fichier, chemin_dest)

            copies += 1
            log(f"[{i}/{total}] Copié : {nom_dest}")

        except Exception as e:
            log(f"[{i}/{total}] ERREUR : {fichier.name} — {e}")
            erreurs += 1

        progress(i, total)

    log("")
    log("=" * 50)
    log("TERMINÉ")
    log(f"Copiés  : {copies}")
    log(f"Ignorés (déjà présents) : {ignores}")
    log(f"Erreurs : {erreurs}")
    log(f"Total analysé : {total}")


# ============================================================
# INTERFACE
# ============================================================

class OngletConversion(QWidget):

    def __init__(self):
        super().__init__()
        self.worker = None
        self._construire_interface()

    def _construire_interface(self):
        layout = QVBoxLayout(self)

        if not HEIC_DISPONIBLE:
            avertissement = QLabel(
                "⚠ Le module 'pillow-heif' n'est pas installé : les fichiers .HEIC "
                "(photos iPhone) seront ignorés. Installe-le avec :\n"
                "pip install pillow-heif"
            )
            avertissement.setWordWrap(True)
            avertissement.setStyleSheet("color: #A32E6D; font-weight: bold;")
            layout.addWidget(avertissement)

        layout.addWidget(QLabel("Dossier source (photos/vidéos à copier) :"))
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

        self.bouton_lancer = QPushButton("Lancer la copie / conversion")
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

        self.worker = Worker(copier_fichiers, source, destination)
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
            QMessageBox.information(self, "Terminé", "La copie/conversion est terminée. Voir le journal pour le détail.")
        else:
            QMessageBox.critical(self, "Erreur", message)
