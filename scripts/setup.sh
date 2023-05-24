#!/bin/bash

: ${NUM_NODES:=6}

: ${MASTER_PORT:=5000}


echo "Opening HTTP Server..."
gnome-terminal --tab --title="http_server" -e "sh -c 'python3 http_server.py'";

echo "Opening Raft Dashboard..."
gnome-terminal --tab --title="client" -e "sh -c 'cd raft-dashboard && npm run dev'";

echo "Starting $NUM_NODES nodes..."

echo "Running leader node on port $MASTER_PORT"
gnome-terminal --tab --title="server0" -e "sh -c 'python3 server.py localhost $MASTER_PORT'";

for (( i=1; i<$NUM_NODES; i++ ))
do
    PORT=$(( MASTER_PORT + i ))

    echo "Running node $i on port $PORT"
    gnome-terminal --tab --title="server$i" -e "sh -c 'python3 server.py localhost $PORT localhost $MASTER_PORT'";
    sleep 1
done

echo "Done starting nodes."

xdg-open "http://localhost:5173"
