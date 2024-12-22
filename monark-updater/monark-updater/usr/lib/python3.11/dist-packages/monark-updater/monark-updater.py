#!/usr/bin/env python3

# We need to modify the path so pistreamer can be run from any location on the pi
import sys
import os

sys.path.insert(0, "/usr/lib/python3.11/dist-packages/monark-updater/")

import subprocess
from time import sleep
from typing import Any, List, Tuple
from constants import (
    BUZZER_PIN,
    DCIM_FOLDER,
    MAX_SD_CARD_CHECKS,
    PUBLIC_KEY_LOCATION,
    SD_CARD_LOCATION,
    SD_CARD_MOUNTED_LOCATION,
    SD_CARD_NAME,
)
import RPi.GPIO as GPIO


class MonarkUpdater:
    def __init__(self) -> None:
        self.total_polls = 0  # we only try up to MAX_SD_CARD_CHECKS
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(BUZZER_PIN, GPIO.OUT)  # Drives buzzer
        except:
            pass

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
                return True
            self._play_failure_buzz()
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

    def verify_and_install_debs(self) -> List[str]:
        file_list = os.listdir(SD_CARD_MOUNTED_LOCATION)
        debs = [f for f in file_list if f.endswith(".deb")]
        if not debs:
            return []
        verified_debs: List[str] = []
        for deb in debs:
            result = self._run_command(
                f'echo "deb [signed-by={PUBLIC_KEY_LOCATION}] file:{SD_CARD_MOUNTED_LOCATION}/monark/ ./" | sudo tee /etc/apt/sources.list.d/local-repo.list',
                no_timeout=True,
            )
            if result.returncode == 0:
                print(f"Verified and installed {deb}.")
            else:
                print(f"Failed to verify {deb}")
        return verified_debs

    def _play_mounted_buzz(self):
        for _ in range(1, 3):
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            sleep(0.1)
            GPIO.output(BUZZER_PIN, GPIO.LOW)
            sleep(0.1)

    def _play_failure_buzz(self):
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        sleep(3)
        GPIO.output(BUZZER_PIN, GPIO.LOW)

    def run(self) -> None:
        while self.total_polls < MAX_SD_CARD_CHECKS:
            is_present, is_mounted = self.is_sd_card_present()
            if is_present and not is_mounted:
                if self.mount_sd_card():
                    print("SD card is mounted.")
                    self._play_mounted_buzz()
                    self.verify_and_install_debs()
            elif is_present and is_mounted:
                print("SD card is mounted and ready.")
                break
            else:
                sleep(3)
                self.total_polls += 1


def main():
    sd_card_service = MonarkUpdater()
    sd_card_service.run()


if __name__ == "__main__":
    main()
