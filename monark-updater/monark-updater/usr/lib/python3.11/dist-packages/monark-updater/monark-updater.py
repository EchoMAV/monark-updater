#!/usr/bin/env python3

# We need to modify the path so pistreamer can be run from any location on the pi
import signal
import sys
import os
from typing import Any, Final, Tuple

INSTALL_PATH: Final = "/usr/lib/python3.11/dist-packages/monark-updater/"
sys.path.insert(0, INSTALL_PATH)

import zipfile
import subprocess
from time import sleep
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
            commands = command.split(" ")
            result = subprocess.run(
                commands,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
            return result
        except Exception as e:
            print(e)
            raise Exception(e)

    def _get_buzzer_process(self, beep_function: str) -> Any:
        """
        Create a background process to play a buzzer sound based on the provided beep_function name from BuzzerService.
        """
        command = [
            "/usr/bin/python3",
            "-c",
            (
                "import sys; "
                f"sys.path.insert(0, '{INSTALL_PATH}'); "
                "from buzzer_service import BuzzerService; "
                f"method_to_call = getattr(BuzzerService(), '{beep_function}'); "
                "method_to_call()"
            ),
        ]
        return subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

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
        buzzer_process = None
        try:
            print(f"Attempting to install {MONARK_UPDATES_ZIP}...")

            # This will start a background process to the buzzer while updates are installing
            buzzer_process = self._get_buzzer_process("triple_heartbeat")

            # Extract the zip file
            extracting_file_path = f"{SD_CARD_MOUNTED_LOCATION}/monark-updates"
            with zipfile.ZipFile(
                f"{SD_CARD_MOUNTED_LOCATION}/{MONARK_UPDATES_ZIP}", "r"
            ) as zip_ref:
                zip_ref.extractall(SD_CARD_MOUNTED_LOCATION)

            print(
                f"Extracted {MONARK_UPDATES_ZIP} to {SD_CARD_MOUNTED_LOCATION}. Attempting to install debs...."
            )

            with open(f"{extracting_file_path}/Packages", "r") as file:
                package_info = file.read()
                print(f"Package info: {package_info}")

            # Ensure echomav public key is loaded in our local repo list
            apt_file = "/etc/apt/sources.list.d"
            self._run_command(f"sudo mkdir -p {apt_file}")
            apt_file = f"{apt_file}/local-repo.list"
            apt_entry = (
                f"deb [signed-by={PUBLIC_KEY_LOCATION}] file:{extracting_file_path} ./"
            )

            os.sync()  # type: ignore
            subprocess.run(
                f'sudo sh -c "echo {apt_entry.strip()} > {apt_file}"',
                shell=True,
                check=True,
            )

            # Perform the update
            update_ret = os.system(
                f'sudo apt -o Dir::Etc::sourcelist="{apt_file}" -o Dir::Etc::sourceparts="-" -o APT::Get::List-Cleanup="0" update',
            )

            if update_ret == 0:
                print("Successfully updated apt")
            else:
                print(f"Failed to update apt: return code {update_ret}")
                buzzer_process.send_signal(signal.SIGTERM)
                BuzzerService().death_beep()
                return

            # Perform the upgrade
            install_ret = self._run_command(
                f"sudo apt install -y pistreamer monark-updater microhard",
                no_timeout=True,
            )
            if install_ret.returncode == 0:
                print("Successfully upgraded pistreamer, monark-updater, and microhard")
            else:
                print(
                    f"Failed to pistreamer, monark-updater, and microhard: {install_ret.stdout} | {install_ret.stderr}"
                )
                buzzer_process.send_signal(signal.SIGTERM)
                BuzzerService().death_beep()  # this is an infinite while loop
                return

            # Clean up operations
            ret = self._run_command(
                f"sudo rm {apt_file}",
                no_timeout=True,
            )
            ret = self._run_command(
                f"sudo rm -rf {extracting_file_path}",
                no_timeout=True,
            )
            ret = self._run_command(
                f"sudo systemctl start video-eo.service",
                no_timeout=True,
            )
            buzzer_process.send_signal(signal.SIGTERM)
            sleep(2)
            BuzzerService().success_beeps()

        except Exception as e:
            print(f"Error occurred: {e}")
            if buzzer_process:
                buzzer_process.send_signal(signal.SIGTERM)

    def run(self) -> None:
        while self.total_polls < MAX_SD_CARD_CHECKS:
            is_present, is_mounted = self.is_sd_card_present()
            if is_present and not is_mounted:
                is_mounted = self.mount_sd_card()

            if is_present and is_mounted:
                print("SD card is mounted.")
                # Stop video-eo service since pistreamer may update
                file_list = os.listdir(SD_CARD_MOUNTED_LOCATION)
                monark_zip = [f for f in file_list if f.endswith(MONARK_UPDATES_ZIP)]
                if not monark_zip:
                    print(f"No monark updates found on SD card")
                    BuzzerService().four_quick_beeps()
                else:
                    self._run_command(
                        f"sudo systemctl stop video-eo.service",
                        no_timeout=True,
                    )
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
