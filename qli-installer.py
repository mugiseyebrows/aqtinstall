#!/usr/bin/env python3
#
# Copyright (C) 2018 Linus Jahn <lnj@kaidan.im>
# Copyright (C) 2019 Hiroshi Miura <miurahr@linux.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import os
import platform
import sys
import subprocess
import urllib.request
import requests
import xml.etree.ElementTree as ElementTree

if len(sys.argv) < 4 or len(sys.argv) > 5:
    print("Usage: {} <qt-version> <host> <target> [<arch>]\n".format(sys.argv[0]))
    print("qt-version:   Qt version in the format of \"5.X.Y\"")
    print("host systems: linux, mac, windows")
    print("targets:      desktop, android, ios")
    print("arch: ")
    print("  target linux/desktop:   gcc_64")
    print("  target mac/desktop:     clang_64")
    print("  target mac/ios:         ios")
    print("  windows/desktop:        win64_msvc2017_64, win64_msvc2015_64")
    print("                          in32_msvc2015, win32_mingw53")
    print("  android:                android_x86, android_armv7")
    exit(1)

base_url = "https://download.qt.io/online/qtsdkrepository/"

# Qt version
qt_version = sys.argv[1]
qt_ver_num = qt_version.replace(".", "")
# one of: "linux", "mac", "windows"
os_name = sys.argv[2]
# one of: "desktop", "android", "ios"
target = sys.argv[3]

# Target architectures:
#
# linux/desktop:   "gcc_64"
# mac/desktop:     "clang_64"
# mac/ios:         "ios"
# windows/desktop: "win64_msvc2017_64", "win64_msvc2015_64",
#                  "win32_msvc2015", "win32_mingw53"
# android:       "android_x86", "android_armv7"

arch = ""
arch_dir = ""
if len(sys.argv) == 5:
    arch = sys.argv[4]
    if arch.startswith('win'):
        arch_dir = arch[6:]
    else:
        arch_dir = arch
elif os_name == "linux" and target == "desktop":
    arch = "gcc_64"
    arch_dir = arch
elif os_name == "mac" and target == "desktop":
    arch = "clang_64"
    arch_dir = arch
elif os_name == "mac" and target == "ios":
    arch = "ios"
    arch_dir = arch

if arch == "":
    print("Please supply a target architecture.")
    exit(1)

# Build repo URL
packages_url = base_url
if os_name == "windows":
    packages_url += os_name + "_x86/"
else:
    packages_url += os_name + "_x64/"
packages_url += target + "/"
packages_url += "qt5_" + qt_ver_num + "/"

# Get packages index
update_xml_url = packages_url + "Updates.xml"
reply = requests.get(update_xml_url)
update_xml = ElementTree.fromstring(reply.content)

package_desc = ""
full_version = ""
archives = []
archives_url = ""
for packageupdate in update_xml.findall("PackageUpdate"):
    name = packageupdate.find("Name").text
    if name == "qt.qt5.{}.{}".format(qt_ver_num, arch) or name == "qt.{}.{}".format(qt_ver_num, arch):
        full_version = packageupdate.find("Version").text
        archives = packageupdate.find("DownloadableArchives").text.split(", ")
        package_desc = packageupdate.find("Description").text
        if ".qt5." in name:
            archives_url = packages_url + "qt.qt5.{}.{}/".format(qt_ver_num, arch)
        else:
            archives_url = packages_url + "qt.{}.{}/".format(qt_ver_num, arch)
        break

if not full_version or not archives:
    print("Error while parsing package information!")
    exit(1)

base_dir= os.path.join(os.getcwd(), 'Qt{}'.format(qt_version))
if not os.path.exists(base_dir):
    os.mkdir(base_dir)
elif not os.path.isdir(base_dir):
    os.unlink(base_dir)
    os.mkdir(base_dir)
os.chdir(base_dir)

print("****************************************")
print("Installing {}".format(package_desc))
print("****************************************")
print("HOST:      ", os_name)
print("TARGET:    ", target)
print("ARCH:      ", arch)
print("Source URL:", archives_url)
print("****************************************")
print("into:      ", base_dir)

for archive in archives:
    url = archives_url + full_version + archive

    sys.stdout.write("\033[K")
    print("Downloading {}...".format(archive), end="\r")
    urllib.request.urlretrieve(url, archive)
    sys.stdout.write("\033[K")
    print("Extracting {}...".format(archive), end="\r")
    if platform.system() is 'Windows':
        subprocess.run([r'C:\Program Files\7-Zip\7z.exe', 'x', '-aoa', '-y', archive])
    else:
        subprocess.run([r'7z', 'x', '-aoa', '-y', archive])
    os.unlink(archive)

f = open(os.path.join(base_dir, qt_version, arch_dir, 'bin', 'qt.conf'), 'w')
f.write("[Paths]\n")
f.write("Prefix=..\n")
f.close()

sys.stdout.write("\033[K")
print("Finished installation")
