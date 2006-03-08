Iraq Net
========

Subversion repository: [https://russ.yanofsky.org/viewvc.py/net](https://russ.yanofsky.org/viewvc.py/net)

Various scripts and configuration files used to manage a satellite internet
gateway on a linux box I set up while deployed in Iraq. There are scripts that
control *iptables* and *tc* to perform traffic control and nat, block
unauthorized computers from accessing the internet, and redirect new computers
attempting to access the internet to a web interface where they can register
and instantly enable access. The web interface is implemented in Mod_Python and
along with registration pages also includes utilities to check the status of
the satellite connection and monitor bandwidth usage. Other interesting things
in the repository include a small DNS proxy server written in Python and some
scripts to deal with configuration files stored in Subversion repositories.
