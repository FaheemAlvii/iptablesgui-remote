# iptablesgui-remote
Remotely Manage your IPTables using GUI based on ssh connection.

1. Make Sure Python3 is installed
2. pip3 install flask paramiko
3. Open multi-server.py and add Servers in this format:
      SERVERS = [
          {'name': 'Server 1', 'host': 'yourserverip', 'username': 'root', 'password': 'serverpass'},
          {'name': 'Server 2', 'host': 'yourserverip', 'username': 'root', 'password': 'serverpass'},
          {'name': 'Server 3', 'host': 'yourserverip', 'username': 'root', 'password': 'serverpass'}
      ]

4. python multi-server.py | python3 multi-server.py
