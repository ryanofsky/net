#!/usr/bin/env python

import sys
import os
import re
import shutil
import getopt

_re_origfile = re.compile(r'^\._cfg\d{4}_(.+)$')

def cpetc(src, dest, overwrite, move, pretend):
  copied_files = {}
  for src_dir, dirnames, filenames in os.walk(src):
    # haven't really experimented with os.walk function so I'll just
    # assume these are true for now and figure out what do to later
    # if they aren't
    assert src_dir[:len(src)] == src
    assert len(src_dir) == len(src) or src_dir[len(src)] == os.sep

    dest_dir = None
    for filename in filenames:
      m = _re_origfile.match(filename)
      if m:
        if dest_dir is None:
          dest_dir = os.path.join(dest, src_dir[len(src)+1:])
          if not pretend:
            os.makedirs(dest_dir)
        
        src_file = os.path.join(src_dir, filename)
        dest_file = os.path.join(dest_dir, m.group(1))

        if copied_files.has_key(dest_file):
          print "[ignoring duplicate original %s]" % src_file
          continue

        exists = os.path.exists(dest_file)
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
        elif move:
          os.rename(src_file, dest_file)
        else:
          shutil.copy2(src_file, dest_file)

def usage():
  sys.stderr.write("""\
Usage: cpetc.py [OPTION] SOURCE DEST
Copy configuration files installed by gentoo packages from SOURCE to DEST

Options:
  -f, --force      Overwrite existing files instead of skipping them
  -r, --remove     Remove files from SOURCE after copying
  -p, --pretend    Don't actually copy files, but produce normal output
                   showing what would be copied
""")
_opts = 'frp'
_longopts = (
  'force',
  'remove',
  'pretend'
)

if __name__ == '__main__':
  try:
    optvals, args = getopt.getopt(sys.argv[1:], _opts, _longopts)
  except getopt.GetoptError, e:
    print >> sys.stderr, e
    usage()
    sys.exit(1)

  overwrite = move = pretend = 0
  for option, value in optvals:
    if option in ('-f', '--force'):
      overwrite = 1
    elif option in ('-r', '--remove'):
      move = 1
    elif option in ('-p', '--pretend'):
      pretend = 1

  if len(args) == 2:
    source, dest = args
  else:
    usage()
    sys.exit(1)

  if not os.path.isdir(source):
    print 'Error: SOURCE argument %s is not a directory' % source
    sys.exit(1)

  if not os.path.isdir(dest):
    print 'Error: DEST argument %s is not a directory' % dest
    sys.exit(1)
 
  cpetc(source, dest, overwrite, move, pretend)
