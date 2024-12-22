# monark-updater
Checks for sd card activity and performs system updates if necessary.

# DEB Software Updates
EchoMAV DEB packages are distrubted through private apt repos and signed with an EchoMAV private key. The MONARK build has the corresponding public key loaded. Repos outside of standard debian/rpi/EchoMAV channels will not auto install.

To build official EchoMAV repo distributions, first import the private key into your build environment via `gpg --import private-key.asc`.

Optionally you may remove via `shred -u private-key.asc`.

# Buzzer Specs
See `buzzer_service.py` for details.
