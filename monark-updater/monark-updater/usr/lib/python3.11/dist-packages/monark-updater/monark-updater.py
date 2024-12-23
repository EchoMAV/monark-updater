#!/usr/bin/env python3

# We need to modify the path so pistreamer can be run from any location on the pi
import sys
import os
import zipfile

sys.path.insert(0, "/usr/lib/python3.11/dist-packages/monark-updater/")
ON_DURATION = 0.08

import subprocess
from time import sleep
from typing import Any, List, Tuple
from constants import (
    DCIM_FOLDER,
    MAX_SD_CARD_CHECKS,
    MONARK_UPDATES_ZIP,
    PUBLIC_KEY_LOCATION,
    SD_CARD_LOCATION,
    SD_CARD_MOUNTED_LOCATION,
    SD_CARD_NAME,
)

from buzzer_service import BuzzerService


class MonarkUpdater:
    def __init__(self) -> None:
        self.total_polls = 0  # we only try up to MAX_SD_CARD_CHECKS

    def _run_command(self, command: str, no_timeout: bool = False) -> Any:
        try:
            timeout = 320 if no_timeout else 2
            result = subprocess.run(
                command.split(" "),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
            return result
        except Exception as e:
            print(e)
            raise Exception(e)

    def is_sd_card_present(self) -> Tuple[bool, bool]:
        """
        Return a tuple indicating if the sd card is present and if it is mounted.
        """
        try:
            result = self._run_command("sudo lsblk")
            is_sd_card_present = SD_CARD_NAME in result.stdout
            is_mounted = SD_CARD_MOUNTED_LOCATION in result.stdout
            return is_sd_card_present, is_mounted
        except Exception as e:
            print(f"Error occurred: {e}")
            return False, False

    def mount_sd_card(self) -> bool:
        try:
            self._run_command(f"sudo mkdir -p {SD_CARD_MOUNTED_LOCATION}")
            result = self._run_command(
                f"sudo mount -o sync,fmask=0000,dmask=0000 {SD_CARD_LOCATION} {SD_CARD_MOUNTED_LOCATION}"
            )
            if result.returncode == 0:
                # make sure DCIM folder exists for saving images/video
                self._run_command(f"sudo mkdir -p {DCIM_FOLDER}")
                os.sync()  # type: ignore
                BuzzerService().quick_beep()
                return True
            BuzzerService().long_beep()
            return False
        except Exception as e:
            print(f"Error occurred: {e}")
            return False

    def unmount_sd_card(self) -> bool:
        try:
            os.makedirs(SD_CARD_MOUNTED_LOCATION, exist_ok=True)
            result = self._run_command(f"sudo umount {SD_CARD_MOUNTED_LOCATION}")
            if result.returncode == 0:
                return True
            return False
        except Exception as e:
            print(f"Error occurred: {e}")
            return False

    def verify_and_install_debs(self) -> None:
        file_list = os.listdir(SD_CARD_MOUNTED_LOCATION)
        monark_zip = [f for f in file_list if f.endswith(MONARK_UPDATES_ZIP)]
        if not monark_zip:
            print(f"No monark updates found on SD card")
            return

        print(f"Attempting to install {MONARK_UPDATES_ZIP}...")

        # Specify the path to the zip file and the extraction directory
        extracting_file_path = f"{SD_CARD_MOUNTED_LOCATION}/monark-updates"

        # ensure echomav public key is installed (prevent duplicate entries)
        apt_entry = (
            f"deb [signed-by={PUBLIC_KEY_LOCATION}] file:{extracting_file_path} ./"
        )
        apt_file = "/etc/apt/sources.list.d/local-repo.list"
        add_entry = False
        if os.path.exists(apt_file):
            with open(apt_file, "r") as f:
                contents = f.read().split("\n")
                if apt_entry not in contents:
                    add_entry = True
        if add_entry:
            self._run_command(
                f'echo "{apt_entry.strip()}" | sudo tee {apt_file}',
                no_timeout=True,
            )

        ret = self._run_command(
            f"sudo apt update",
            no_timeout=True,
        )
        print(ret)

        # Extract the zip file
        with zipfile.ZipFile(
            f"{SD_CARD_MOUNTED_LOCATION}/{MONARK_UPDATES_ZIP}", "r"
        ) as zip_ref:
            zip_ref.extractall(SD_CARD_MOUNTED_LOCATION)

        print(
            f"Extracted {MONARK_UPDATES_ZIP} to {SD_CARD_MOUNTED_LOCATION}. Attempting to install debs...."
        )

        ret = self._run_command(
            f"sudo apt install pistreamer monark-updater microhard",
            no_timeout=True,
        )
        print(ret)

    def run(self) -> None:
        while self.total_polls < MAX_SD_CARD_CHECKS:
            is_present, is_mounted = self.is_sd_card_present()
            if is_present and not is_mounted:
                if self.mount_sd_card():
                    print("SD card is mounted.")
                    self.verify_and_install_debs()
            elif is_present and is_mounted:
                print("SD card is mounted and ready.")
                self.verify_and_install_debs()
                break
            else:
                sleep(3)
                self.total_polls += 1


def main():
    sd_card_service = MonarkUpdater()
    sd_card_service.run()


if __name__ == "__main__":
    main()
