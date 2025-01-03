# Design
This repo houses the three main software packages needed for MONARK:

* `pistreamer`
* `microhard`
* `monark-updater`

This repo, `monark-updater`, references `pistreamer` and `microhard` as submodules and `monark-updater` as it's own folder structure (note the dash which is in keep with debian package convention).

# How to Build Automatically
(You will need private-key.asc on your developer machine in order to signed our private repo.)
* Make changes on your developer machine to `pistreamer`, `microhard`, and `monark-updater` as desired.
* Run `python _build_all_on_target.py` on developer machine.
* Source control all the changes in each repo and push.

# How to Build Manually
* If updates are required in any of the three packages above, make modifications to the python files in `{package}/usr/lib/python3.11/dist-packages/{package}/*`.
* Consider whether you want to modify the source control version under `{package}/DEBIAN/control`.
* After making changes to the source code of a package, copy the package folder onto a RPi.
* On the RPi, navigate to the package folder and run `make_debian.sh`.
* Copy the outputted `.deb` file back into the git repo on your development machine and check it in.
* Copy or clone the entire contents of `monark-updater` repo on your RPi.
* On the RPi set the env var `export PASSPHRASE={thepassphrase}` then run `make_debian_repo.sh`. The release file `private-key.asc` but also be located on the RPi so the apt repo is signed properly. That is very important.
* The output of this operation `monark-updates.zip` is what a MONARK user must copy to an SD card and place in the MONARK before boot up. The packages will automatically install after boot up (the service `monark-updater` takes care of doing that).

To copy all the source controllable assets from the RPi to your development machine run the following from the root folder of the repo:

```
export RPI_IP=192.168.1.28 # change
export PACKAGE_VERSION=1.1.1 # change
scp echopilot@${RPI_IP}:~/monark-updater/monark-updates.zip .
scp echopilot@${RPI_IP}:~/monark-updater/monark-updater/monark-updater_${PACKAGE_VERSION}_arm64.deb monark-updater/
scp echopilot@${RPI_IP}:~/monark-updater/pistreamer/pistreamer_${PACKAGE_VERSION}_arm64.deb pistreamer/
scp echopilot@${RPI_IP}:~/monark-updater/microhard/microhard_${PACKAGE_VERSION}_arm64.deb microhard/
```

# DEB Software Updates
EchoMAV DEB packages are distributed through private apt repos and signed with an EchoMAV private key. The MONARK build has the corresponding public key loaded. Repos outside of standard debian/rpi/EchoMAV channels will not auto install.

# Create a new private/public key
```
gpg --batch --gen-key <<EOF
Key-Type: RSA
Key-Length: 2048
Subkey-Type: RSA
Subkey-Length: 2048
Name-Real: MONARK
Name-Email: monark@echomav.com
Expire-Date: 0
Passphrase: YOUR_PASSPHRASE
EOF
```
```
gpg --export-secret-keys --armor "MONARK" > private-key.asc
gpg --export "MONARK" > public-key.gcs
```
