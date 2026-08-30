"""
Onglet : Import des photos/vidéos depuis un iPhone branché.

La logique métier (fonctions ci-dessous) est reprise TELLE QUELLE de
transfert_photos_iphone.py, avec deux adaptations :
    - le téléchargement (subprocess) est lu ligne par ligne pour
      afficher sa sortie en direct dans le journal, au lieu d'attendre
      la fin en bloc
    - plus de input()/print()/sys.exit() : tout passe par log(message)
      et par des messages dans l'interface
"""

import io
import shutil
import contextlib
import sys
from pathlib import Path

from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_DISPONIBLE = True
except ImportError:
    HEIC_DISPONIBLE = False

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QTextEdit, QProgressBar, QMessageBox, QCheckBox
)

from worker import Worker


PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".heic", ".heif", ".png")
VIDEO_EXTENSIONS = (".mov", ".mp4")

RAW_SUBDIR_NAME = "_raw_iphone_dcim"


# ============================================================
# LOGIQUE MÉTIER (reprise de transfert_photos_iphone.py)
# ============================================================

class _RelaisLog(io.TextIOBase):
    """
    Redirige, ligne par ligne, tout ce qui est écrit sur stdout/stderr
    vers le journal de l'interface. Utilisé pour capturer la sortie de
    pymobiledevice3 quand on l'appelle directement en interne.
    """

    def __init__(self, fonction_log):
        self._log = fonction_log
        self._tampon = ""

    def write(self, texte):
        self._tampon += texte
        while "\n" in self._tampon:
            ligne, self._tampon = self._tampon.split("\n", 1)
            if ligne.strip():
                self._log(ligne)
        return len(texte)

    def flush(self):
        if self._tampon.strip():
            self._log(self._tampon)
        self._tampon = ""


def pull_dcim(log, raw_dir: Path) -> bool:
    """
    Récupère tout le contenu de /DCIM depuis l'iPhone vers raw_dir.

    Important : on appelle directement la bibliothèque pymobiledevice3
    (au lieu de lancer "python -m pymobiledevice3" dans un sous-processus,
    comme dans le script original). C'est nécessaire car une fois l'appli
    empaquetée en .exe avec PyInstaller, sys.executable pointe vers l'exe
    lui-même et non vers Python, donc "sys.executable -m pymobiledevice3"
    ne fonctionnerait plus.

    Renvoie True si le téléchargement a réussi, False sinon.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)

    log("Connexion à l'iPhone et téléchargement de /DCIM en cours...")
    log("(cela peut prendre du temps selon le nombre de photos/vidéos)")
    log("")

    ancien_argv = sys.argv
    relais = _RelaisLog(log)
    succes = True

    try:
        sys.argv = ["pymobiledevice3", "afc", "pull", "/DCIM", str(raw_dir)]
        from pymobiledevice3.__main__ import main as pymobiledevice3_main

        with contextlib.redirect_stdout(relais), contextlib.redirect_stderr(relais):
            try:
                pymobiledevice3_main()
            except SystemExit as e:
                succes = e.code is None or e.code == 0

    except Exception as e:
        relais.flush()
        log(f"Erreur inattendue : {e}")
        succes = False

    finally:
        relais.flush()
        sys.argv = ancien_argv

    if not succes:
        log("")
        log("Le téléchargement a échoué (voir le message ci-dessus).")
        log("Vérifie que :")
        log("  - le téléphone est branché, déverrouillé")
        log("  - tu as accepté 'Faire confiance à cet ordinateur' sur l'écran")

    return succes


def find_media_files(raw_dir: Path):
    fichiers = []
    for chemin in raw_dir.rglob("*"):
        if chemin.is_file() and chemin.suffix.lower() in PHOTO_EXTENSIONS + VIDEO_EXTENSIONS:
            fichiers.append(chemin)
    return fichiers


def convert_to_jpg(raw_data: bytes) -> bytes:
    with Image.open(io.BytesIO(raw_data)) as img:
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=92, exif=img.info.get("exif", b""))
        return buffer.getvalue()


def process_files(log, progress, local_files, dest_dir: Path):
    dest_dir.mkdir(parents=True, exist_ok=True)

    total = len(local_files)
    copies = 0
    ignores = 0
    erreurs = 0

    for i, local_path in enumerate(local_files, start=1):
        ext_lower = local_path.suffix.lower()
        est_photo = ext_lower in PHOTO_EXTENSIONS
        est_heic = ext_lower in (".heic", ".heif")

        if est_heic and not HEIC_DISPONIBLE:
            log(f"[{i}/{total}] IGNORÉ (module HEIC absent) : {local_path.name}")
            erreurs += 1
            progress(i, total)
            continue

        nom_local = f"{local_path.stem}.jpg" if est_photo else local_path.name
        chemin_dest = dest_dir / nom_local

        if chemin_dest.exists():
            ignores += 1
            progress(i, total)
            continue

        try:
            if est_photo:
                data = local_path.read_bytes()
                data = convert_to_jpg(data)
                chemin_dest.write_bytes(data)
            else:
                shutil.copy2(local_path, chemin_dest)
            copies += 1
        except Exception as e:
            log(f"[{i}/{total}] ERREUR : {local_path.name} — {e}")
            erreurs += 1
            progress(i, total)
            continue

        log(f"[{i}/{total}] Traité : {nom_local}")
        progress(i, total)

    log("")
    log("=" * 50)
    log("TERMINÉ")
    log(f"Copiés  : {copies}")
    log(f"Ignorés (déjà présents) : {ignores}")
    log(f"Erreurs : {erreurs}")
    log(f"Total analysé : {total}")


def transferer_iphone(log, progress, destination, garder_brut):
    """
    Fonction principale, lancée dans un thread séparé (voir worker.py).
    """
    dest_dir = Path(destination)
    raw_dir = dest_dir / RAW_SUBDIR_NAME

    # Étape 1 : téléchargement (progression indéterminée : total inconnu)
    progress(0, 0)
    succes = pull_dcim(log, raw_dir)
    if not succes:
        return

    # Étape 2 : recherche des fichiers téléchargés
    log("")
    log("Recherche des photos/vidéos téléchargées...")
    local_files = find_media_files(raw_dir)
    log(f"{len(local_files)} fichier(s) trouvé(s).")
    log("")

    if not local_files:
        log("Aucun fichier trouvé dans le téléchargement.")
        return

    # Étape 3 : conversion / copie (progression déterminée)
    process_files(log, progress, local_files, dest_dir)

    # Étape 4 : nettoyage
    if not garder_brut:
        log("")
        log("Nettoyage du dossier temporaire...")
        shutil.rmtree(raw_dir, ignore_errors=True)


# ============================================================
# INTERFACE
# ============================================================

class OngletIphone(QWidget):

    def __init__(self):
        super().__init__()
        self.worker = None
        self._construire_interface()

    def _construire_interface(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            "Branche ton iPhone, déverrouille-le, et accepte 'Faire confiance à "
            "cet ordinateur' si demandé, avant de lancer l'import."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        if not HEIC_DISPONIBLE:
            avertissement = QLabel(
                "⚠ Le module 'pillow-heif' n'est pas installé : les fichiers .HEIC "
                "seront ignorés. Installe-le avec : pip install pillow-heif"
            )
            avertissement.setWordWrap(True)
            avertissement.setStyleSheet("color: #A32E6D; font-weight: bold;")
            layout.addWidget(avertissement)

        layout.addWidget(QLabel("Dossier de destination sur cet ordinateur :"))
        ligne_dest = QHBoxLayout()
        self.champ_destination = QLineEdit()
        bouton_dest = QPushButton("Parcourir...")
        bouton_dest.clicked.connect(self._choisir_destination)
        ligne_dest.addWidget(self.champ_destination)
        ligne_dest.addWidget(bouton_dest)
        layout.addLayout(ligne_dest)

        self.case_garder_brut = QCheckBox(
            "Garder les fichiers bruts téléchargés (ne pas les supprimer après conversion)"
        )
        layout.addWidget(self.case_garder_brut)

        self.bouton_lancer = QPushButton("Lancer l'import depuis l'iPhone")
        self.bouton_lancer.setObjectName("boutonPrincipal")
        self.bouton_lancer.clicked.connect(self._lancer)
        layout.addWidget(self.bouton_lancer)

        self.barre_progression = QProgressBar()
        layout.addWidget(self.barre_progression)

        layout.addWidget(QLabel("Journal :"))
        self.zone_log = QTextEdit()
        self.zone_log.setReadOnly(True)
        layout.addWidget(self.zone_log)

    def _choisir_destination(self):
        dossier = QFileDialog.getExistingDirectory(self, "Choisir le dossier de destination")
        if dossier:
            self.champ_destination.setText(dossier)

    def _lancer(self):
        destination = self.champ_destination.text().strip()

        if not destination:
            QMessageBox.warning(
                self, "Champ manquant",
                "Merci de choisir un dossier de destination."
            )
            return

        self.zone_log.clear()
        self.barre_progression.setRange(0, 1)
        self.barre_progression.setValue(0)
        self.bouton_lancer.setEnabled(False)

        garder_brut = self.case_garder_brut.isChecked()

        self.worker = Worker(transferer_iphone, destination, garder_brut)
        self.worker.log_signal.connect(self._ajouter_log)
        self.worker.progress_signal.connect(self._maj_progression)
        self.worker.termine_signal.connect(self._fin_traitement)
        self.worker.start()

    def _ajouter_log(self, message):
        self.zone_log.append(message)

    def _maj_progression(self, valeur, total):
        if total == 0:
            # Progression indéterminée (on ne connaît pas encore le nombre
            # de fichiers pendant le téléchargement depuis l'iPhone).
            self.barre_progression.setRange(0, 0)
        else:
            self.barre_progression.setRange(0, total)
            self.barre_progression.setValue(valeur)

    def _fin_traitement(self, succes, message):
        self.bouton_lancer.setEnabled(True)
        self.barre_progression.setRange(0, 1)
        if succes:
            QMessageBox.information(self, "Terminé", "L'import est terminé. Voir le journal pour le détail.")
        else:
            QMessageBox.critical(self, "Erreur", message)
