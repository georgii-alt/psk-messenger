[app]
title = PSK Messenger
package.name = pskmessenger
package.domain = org.georgii
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.1
requirements = python3,kivy,kivymd,requests,urllib3,chardet,idna,certifi
orientation = portrait
osx.kivy_version = 2.3.1
fullscreen = 0
android.archs = arm64-v8a
# Даем мессенджеру доступ к файлам и галерее на телефоне
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

[buildozer]
log_level = 2
warn_on_root = 1
