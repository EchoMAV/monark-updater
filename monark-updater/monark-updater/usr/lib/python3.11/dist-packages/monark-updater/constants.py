#!/usr/bin/env python3
from typing import Final

SD_CARD_NAME: Final = "mmcblk1p1"
SD_CARD_LOCATION: Final = f"/dev/{SD_CARD_NAME}"
SD_CARD_MOUNTED_LOCATION: Final = "/mnt/external_sd"
DCIM_FOLDER: Final = f"{SD_CARD_MOUNTED_LOCATION}/DCIM"
MAX_SD_CARD_CHECKS: Final = 15
PUBLIC_KEY_LOCATION: Final = (
    "/usr/share/keyrings/monark-keyring.gpg"  # must not be armored file
)
MONARK_UPDATES_ZIP: Final = "monark-updates.zip"
