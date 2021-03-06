#!/usr/bin/python
#   SparkleShare, an instant update workflow to Git.
#   Copyright (C) 2010  Hylke Bons <hylkebons@gmail.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import shutil
import time

import gio
import nautilus

import pygtk
pygtk.require('2.0')
import gtk

SPARKLESHARE_PATH = os.path.join (os.path.expanduser ('~'), "SparkleShare")

import gettext
gettext.bindtextdomain('sparkleshare', '/usr/share/locale')
gettext.textdomain('sparkleshare')
_ = gettext.gettext

class SparkleShareExtension (nautilus.MenuProvider):


    def __init__ (self):

        debug = "Loaded Nautilus SparkleShare Extension."


    def checkout_version (self, menu, file_reference, commit_hash, username, timestamp):

        file_name = file_reference.get_basename ().replace (" ", "\ ").replace ("(", "\(").replace (")", "\)")
        file_path = file_reference.get_path ().replace (" ", "\ ").replace ("(", "\(").replace (")", "\)")
        tmp_file_path = os.path.join (SPARKLESHARE_PATH, ".tmp", file_reference.get_basename ())

        # Move the current version to a temporary path
        shutil.move (file_reference.get_path (), tmp_file_path)

        # Check out the earlier version
        os.chdir (file_reference.get_parent ().get_path ())
        os.popen ("git checkout " + commit_hash + " " + file_name
            .replace (" ", "\ ").replace ("(", "\(").replace (")", "\)"))

        new_tmp_file_name = file_name + " (" + username + ", "
        new_tmp_file_name += time.strftime ("%H:%M %d %b %Y", timestamp).replace (" 0", " ") + ") "

        # Rename the checked out file
        shutil.move (file_name, new_tmp_file_name)

        # Move the original file back
        shutil.move (tmp_file_path, file_path)

        return True


    def copy_web_link (self, menu, file_reference):

        path = file_reference.get_path ()

        # Get the remote url used for the repo
        url_command = os.popen ("git config --get remote.origin.url")
        url = url_command.readline ().strip ()

        # Strip the unneeded parts
        url = url.lstrip ("ssh://git")
        url = url.lstrip ("@")
        url = url.rstrip (".git")

        # Format the right web url depending on the service
        relative_path = path.lstrip (SPARKLESHARE_PATH)
        repo_name = relative_path [:relative_path.find ("/")]
        relative_path = relative_path.lstrip (repo_name)

        if "gitorious.org" in url:
	        url = "http://" + url + "/blobs/master" + relative_path
        if "github.com" in url:
            url = "http://" + url + "/raw/master" + relative_path

        url = url.replace (" ", "%20");

        clipboard = gtk.clipboard_get ()
        clipboard.set_text (url)
        clipboard.store ()

        return


    def get_file_items (self, window, files):

		# Only work if one file is selected
        if len (files) != 1:
            return

        file_reference = gio.File (files [0].get_uri ())

		# Only work if we're in a SparkleShare repository folder
        if not (file_reference.get_path ().startswith (SPARKLESHARE_PATH)):
            return

        web_link_menu_item = nautilus.MenuItem ("Nautilus::CopyWebLink", _("Copy Web Link"),
                                                _("Copy the web address of this file to the clipboard"))

        web_link_menu_item.connect ("activate", self.copy_web_link, file_reference)


        epochs        = ["", "", "", "", "", "", "", "", "", ""]
        commit_hashes = ["", "", "", "", "", "", "", "", "", ""]

        os.chdir (file_reference.get_parent ().get_path ())

        time_command   = os.popen ("git log -10 --format='%at' " + file_reference.get_basename ()
            .replace (" ", "\ ").replace ("(", "\(").replace (")", "\)"))

        author_command = os.popen ("git log -10 --format='%an' " + file_reference.get_basename ()
            .replace (" ", "\ ").replace ("(", "\(").replace (")", "\)"))

        hash_command = os.popen ("git log -10 --format='%H' " + file_reference.get_basename ()
            .replace (" ", "\ ").replace ("(", "\(").replace (")", "\)"))

        i = 0
        for line in time_command.readlines ():
            epochs [i] = line.strip ("\n")
            i += 1

        # Only work if there is history
        if i < 2:
            return web_link_menu_item,

        i = 0
        for line in hash_command.readlines ():
            commit_hashes [i] = line.strip ("\n")
            i += 1

        earlier_version_menu_item = nautilus.MenuItem ("Nautilus::OpenOlderVersion", _("Get Earlier Version"),
                                                       _("Make a copy of an earlier version in this folder"))
        submenu = nautilus.Menu ()

        i = 0
        for line in author_command.readlines ():

            if i > 0:

                timestamp = time.strftime ("%d %b\t%H:%M", time.localtime (float (epochs [i])))
                username = line.strip ("\n")

                menu_item = nautilus.MenuItem ("Nautilus::Version" + epochs [i],
                                           timestamp + "\t" + username,
                                           _("Select to get a copy of this version"))

                menu_item.connect ("activate", self.checkout_version, file_reference, commit_hashes [i],
                                   username, time.localtime (float (epochs [i])))
                submenu.append_item (menu_item)

            i += 1

        earlier_version_menu_item.set_submenu (submenu)


        return earlier_version_menu_item, web_link_menu_item
