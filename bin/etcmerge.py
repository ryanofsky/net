#!/usr/bin/env python

import sys
import os
import re
import shutil
import getopt


def etcmerge(repos, first, second):
  sys.stdout.write("svn copy -m '* vendor/etc/r%(second)i\n"
                   "    tag of vendor/etc/current:%(second)i "
                   "before merge into trunk/etc' "
                   "-r %(second)s "
                   "%(repos)s/vendor/etc/current "
                   "%(repos)s/vendor/etc/r%(second)i\n\n"
                   
                   "svn co %(repos)s/trunk/etc tmp\n\n"

                   "cd tmp\n\n"

                   "svn merge "
                   "%(repos)s/vendor/etc/r%(first)i "
                   "%(repos)s/vendor/etc/r%(second)i\n\n"

                   "cd ..\n\n"

                   "cpwc.py tmp .\n\n"

                   "rm -rf tmp\n\n"

                   "find . -name '*.new.*'\n" % 
                   {'repos': repos, 'first': first, 'second': second})
  
def usage():
  sys.stderr.write("""\
Usage: etcmerge.py REPOS_URL OLD_REV NEW_REV
Print commands for merging vendor/etc/current to /etc

REPOS_URL is the URL of the subversion repository
OLD_REV is the last revision of vendor/etc/current that was
  merged
NEW_REV is the revision of vendor/etc/current that is about
  to be merged, i.e. the latest repository revision
""")

if __name__ == '__main__':

  if len(sys.argv) == 4:
    repos_url, old_rev, new_rev = sys.argv[1:]
  else:
    usage()
    sys.exit(1)

  error = False
  try:
    old_rev = int(old_rev)
  except ValueError:
    print 'Error: Invalid OLD_REV argument', old_rev
    error = True
  try:
    new_rev = int(new_rev)
  except ValueError:
    print 'Error: Invalid NEW_REV argument', new_rev
    error = True

  if error:
    sys.exit(1)

  etcmerge(repos_url, old_rev, new_rev)
