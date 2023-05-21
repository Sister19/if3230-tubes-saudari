#!/bin/bash

gnome-terminal --tab --title='server1' -e "bash -c 'python3 server.py localhost 5000'";
gnome-terminal --tab --title='server2' -e "bash -c 'python3 server.py localhost 5001 localhost 5000'";
gnome-terminal --tab --title='server3' -e "bash -c 'python3 server.py localhost 5002 localhost 5000'"

gnome-terminal --tab --title='http_server' -e "bash -c 'python3 http_server.py'"
gnome-terminal --tab --title='client' -e "bash -c 'cd raft-dashboard && npm run dev'"
