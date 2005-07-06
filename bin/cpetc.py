#!/usr/bin/env python

import sys
import os
import re
import shutil
import getopt

_re_update_file = re.compile(r'^\._cfg\d{4}_(.+)$')

def cpetc(selection, src, dest, overwrite, move, pretend):
  copied_files = {}
  for src_dir, dirnames, filenames in os.walk(src):
    # haven't really experimented with os.walk function so I'll just
    # assume these are true for now and figure out what do to later
    # if they aren't
    assert src_dir[:len(src)] == src
    assert len(src_dir) == len(src) or src_dir[len(src)] == os.sep

    dest_dir = os.path.join(dest, src_dir[len(src)+1:])

    for filename in filenames:
      src_file = os.path.join(src_dir, filename)

      if selection == UPDATES:
        m = _re_update_file.match(filename)
        if not m:
          continue

        dest_file = os.path.join(dest_dir, m.group(1))

        if copied_files.has_key(dest_file):
          print "[ignoring duplicate original %s]" % src_file
          continue
        else:
          copied_files[dest_file] = None

      else:
        dest_file = os.path.join(dest_dir, filename)

      exists = os.path.exists(dest_file)

      if selection == EXISTING and not exists:
        continue
        
      print (move and "mv" or "cp"), src_file, dest_file,
      if exists:
        if overwrite:
          print "[overwriting]"
        else:
          print "[skipping]"
          continue
      else:
        print

      if pretend:
        continue
        
      os.makedirs(dest_dir)
      if move:
        os.rename(src_file, dest_file)
      else:
        shutil.copy2(src_file, dest_file)

def usage():
  sys.stderr.write("""\
Usage: cpetc.py [OPTION] SELECTION SOURCE DEST
Copy selected configuration files from SOURCE to DEST directories.

SELECTION is one of:
 ALL               copy all files under the source directory
 EXISTING          copy only files under the source directory that already 
                   exist under the destination directory (use with --force
                   option for effect)
 UPDATES           copy and rename only updated configuration files installed
                   by gentoo packages (._cfg* files)

Options:
  -f, --force      Overwrite existing files instead of skipping them
  -r, --remove     Remove files from SOURCE after copying
  -p, --pretend    Don't actually copy files, but produce normal output
                   showing what would be copied
""")

_opts = 'frp'
_longopts = ('force', 'remove', 'pretend')
_selections = ('ALL', 'EXISTING', 'UPDATES')

for s in _selections: globals()[s] = s

if __name__ == '__main__':
  try:
    optvals, args = getopt.getopt(sys.argv[1:], _opts, _longopts)
  except getopt.GetoptError, e:
    print >> sys.stderr, e
    sys.exit(1)

  overwrite = move = pretend = 0
  for option, value in optvals:
    if option in ('-f', '--force'):
      overwrite = 1
    elif option in ('-r', '--remove'):
      move = 1
    elif option in ('-p', '--pretend'):
      pretend = 1

  if len(args) == 3:
    selection, source, dest = args
  else:
    usage()
    sys.exit(1)

  error = False
  if not selection in _selections:
    print 'Error: Invalid SELECTION argument', selection
    error = True
  if not os.path.isdir(source):
    print 'Error: SOURCE argument %s is not a directory' % source
    error = True
  if not os.path.isdir(dest):
    print 'Error: DEST argument %s is not a directory' % dest
    error = True

  if error:
    sys.exit(1)

  cpetc(selection, source, dest, overwrite, move, pretend)
