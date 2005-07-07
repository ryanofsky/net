#!/usr/bin/env python

import sys
import os
import re
import shutil
import getopt

def cpwc(src, dest, pretend):
  for src_dir, dirnames, filenames in os.walk(src):
    # haven't really experimented with os.walk function so I'll just
    # assume these are true for now and figure out what do to later
    # if they aren't
    assert src_dir[:len(src)] == src
    assert len(src_dir) == len(src) or src_dir[len(src)] == os.sep

    dest_dir = os.path.join(dest, src_dir[len(src)+1:])

    for dirname in dirnames:
      if dirname == '.svn':
        src_subdir = os.path.join(src_dir, dirname)
        dest_subdir = os.path.join(dest_dir, dirname)
        if os.path.isdir(dest_subdir):
          print "rm", dest_subdir
          if not pretend:
            shutil.rmtree(dest_subdir)
        print "cp", src_subdir, dest_subdir
        if not pretend:
          shutil.copytree(src_subdir, dest_subdir)
        dirnames.remove(dirname)

    for filename in filenames:
      src_file = os.path.join(src_dir, filename)
      dest_file = os.path.join(dest_dir, filename)
      
      if os.path.isfile(dest_file):
        if files_same(src_file, dest_file):
          continue
        dest_file = file_next(dest_file)

      print "cp", src_file, dest_file
      if not pretend:
        shutil.copy2(src_file, dest_file)

def files_same(file1, file2):
  return open(file1).read() == open(file2).read()

def file_next(file):
  if not os.path.exists(file):
    return file

  i = 1
  while 1:
    next_file = "%s.new.%i" % (file, i)
    if not os.path.exists(next_file):
      return next_file
    i += 1

def usage():
  sys.stderr.write("""\
Usage: cpwc.py [OPTION] SOURCE DEST
Copy files from SOURCE working copy to DEST directory, overwriting
any existing WC metadata in DEST, but preserving existing files,
placing new ones alongside with suffixes like .new.1, .new.2.

Options:
  -p, --pretend    Don't actually copy files, but produce normal output
                   showing what would be copied
""")

_opts = 'p'
_longopts = ('pretend')

if __name__ == '__main__':
  try:
    optvals, args = getopt.getopt(sys.argv[1:], _opts, _longopts)
  except getopt.GetoptError, e:
    print >> sys.stderr, e
    sys.exit(1)

  pretend = 0
  for option, value in optvals:
    if option in ('-p', '--pretend'):
      pretend = 1

  if len(args) == 2:
    source, dest = args
  else:
    usage()
    sys.exit(1)

  error = False
  if not os.path.isdir(source):
    print 'Error: SOURCE argument %s is not a directory' % source
    error = True
  if not os.path.isdir(dest):
    print 'Error: DEST argument %s is not a directory' % dest
    error = True

  if error:
    sys.exit(1)

  cpwc(source, dest, pretend)
