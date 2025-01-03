#!/usr/bin/env python3

"""
In order to create publishable updates for any modifications to MONARK packages, run this script on your host machine.

It will copy the current contents of the pistreamer, monark-updater, and microhard directories to the Raspberry Pi,
build the deb files, and copy them back to the local machine.

After that it will call make_debian_repo.sh on the Raspberry Pi to package the deb files into a repository.
"""

import os
import subprocess
import paramiko  # type: ignore
import sys
import time
import glob

deb_version = ""
if len(sys.argv) > 1:
    deb_version = sys.argv[1]
else:
    print(f"After the script name specify the version such as 1.1.2")
    sys.exit(1)


# Change these values to match your setup
rpi_ip = os.environ.get("RPI_IP")
rpi_password = os.environ.get("RPI_PASSWORD")
repo_passphrase = os.environ.get("PASSPHRASE")
if not rpi_ip:
    print("Please set the RPI_IP environment variable.")
    sys.exit(1)
if not rpi_password:
    print("Please set the RPI_PASSWORD environment variable.")
    sys.exit(1)
if not repo_passphrase:
    print("Please set the PASSPHRASE environment variable to build the signed repo.")
    sys.exit(1)

# Define directories and command
pistreamer_dir = "pistreamer"
microhard_dir = "microhard"
monark_updater_dir = "monark-updater"


def build_deb_on_rpi(command: str, parse_output: bool = True) -> str:
    # Create SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the remote host
        client.connect(rpi_ip, port=22, username="echopilot", password=rpi_password)
        # Execute the command
        stdin, stdout, stderr = client.exec_command(command)
        if parse_output:
            print(f"Connected to {rpi_ip}")
            output = stdout.read().decode().strip()
            file_name = ""
            if "=======-------=======" in output:
                file_name = (
                    output.split("=======-------=======")[1]
                    .split("Add ./")[1]
                    .split(" to source")[0]
                    .strip()
                )
            else:
                raise Exception(f"Failed to build deb file: {output}")
            return file_name
        return ""

    except Exception as e:
        print(f"Failed to execute command: {e}")
        return ""

    finally:
        # Close the connection
        client.close()
        print(f"Connection to {rpi_ip} closed.")


has_error = False
for dir_x in [pistreamer_dir, monark_updater_dir, microhard_dir]:
    try:
        os.chdir(dir_x)
        print("Updating version in the package...")

        # Update the deb version in control file
        lines = []
        file_name = f"./{dir_x}/DEBIAN/control"
        with open(file_name, "r") as file:
            lines = file.readlines()
        with open(file_name, "w") as file:
            for line in lines:
                if line.startswith("Version:"):
                    file.write(f"Version: {deb_version}\n")
                else:
                    file.write(line)

        # Remove old .deb files
        deb_files = glob.glob(os.path.join(os.getcwd(), "*.deb"))
        for file_path in deb_files:
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Failed to remove {file_path}: {e}")

        # Copy the files to the Raspberry Pi
        build_deb_on_rpi(f"rm -rf {dir_x}", parse_output=False)
        print(f"Running commands for {dir_x}...")
        subprocess.run(
            f"scp -r * echopilot@{rpi_ip}:~/{dir_x}",
            shell=True,
            check=True,
            text=True,
            capture_output=True,
        )

        # Make the new deb
        deb_file = build_deb_on_rpi(f"cd ~/{dir_x} && ./make_debian.sh")
        if deb_file:
            print(f"Deb file built: {deb_file}")
            subprocess.run(
                f"scp echopilot@{rpi_ip}:~/{dir_x}/{deb_file} .",
                shell=True,
                check=True,
                text=True,
                capture_output=True,
            )
        else:
            has_error = True
        os.chdir("..")
        time.sleep(4)
    except Exception as e:
        has_error = True
        print(f"Error occurred while executing command: {e}")

# Now that we have the debs we create the repo
try:
    print(f"Running commands to create the repository...")
    build_deb_on_rpi(f"rm -rf monark-updater", parse_output=False)
    subprocess.run(
        f"scp -r * echopilot@{rpi_ip}:~/monark-updater",
        shell=True,
        check=True,
        text=True,
        capture_output=True,
    )
    repo_file = build_deb_on_rpi(
        f"export PASSPHRASE={repo_passphrase} && cd ~/monark-updater && ./make_debian_repo.sh"
    )
    if repo_file:
        print(f"Repo built: {repo_file}")
        subprocess.run(
            f"scp echopilot@{rpi_ip}:~/monark-updater/{repo_file} .",
            shell=True,
            check=True,
            text=True,
            capture_output=True,
        )
    else:
        has_error = True
    os.chdir("..")
except Exception as e:
    has_error = True
    print(f"Error occurred while executing command: {e}")

if not has_error:
    print(
        "Successfully built debs and make a repo. Make the necessary updates to source control and consider publishing the repo."
    )
else:
    print("Failed to build debs and make a repo. Check the logs for more information.")
