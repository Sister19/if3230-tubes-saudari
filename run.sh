#!/bin/bash

gnome-terminal --tab --title='server1' -e "bash -c 'python3 server.py localhost 5000'";
gnome-terminal --tab --title='server2' -e "bash -c 'python3 server.py localhost 5001 localhost 5000'";
gnome-terminal --tab --title='server3' -e "bash -c 'python3 server.py localhost 5002 localhost 5000'"
