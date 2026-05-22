[app]

title = DermaSpectra
package.name = dermaspectra
package.domain = org.dermaspectra

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf

version = 1.0.0
version.regex =
version.build =

requirements = python3,kivy==2.3.1,requests

presplash.filename =
icon.filename =

orientation = portrait

osx.python_version = 3
osx.kivy_version = 2.3.1

osx.codesign = no

# Android
android.api = 34
android.minapi = 21
android.ndk = 27
android.sdk = 34
android.arch = arm64-v8a
android.accept_sdk_license = True
android.permissions = INTERNET
android.private_storage = True
android.allow_download = True

# iOS
ios.codesign = no

[buildozer]

log_level = 2
warn_on_root = 1
