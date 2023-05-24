#!/bin/bash

: ${NUM_NODES:=6}

: ${MASTER_PORT:=5000}

tc qdisc add dev lo root netem delay 1000ms 50ms reorder 8% corrupt 5% duplicate 2% 5% loss 5%

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

echo "Sleeping for 2 seconds..."
sleep 2

arr_cmds=(
    'queue("1")', 'queue("2")', 
    'queue("3")', 'queue("s")', 
    'queue("i")', 'queue("s")')

echo "Sending commands to nodes..."

NUM_FOLLOWERS=$(( NUM_NODES - 1 ))

for (( i=0; i<${#arr_cmds[@]}; i++ ))
do
    PORT=$(( 1 + MASTER_PORT + i % NUM_FOLLOWERS ))

    echo "Sending command ${arr_cmds[$i]} to node $i on port $PORT"
    gnome-terminal --tab --title="client$i" -e "sh -c 'python3 one_cmd_client.py localhost $PORT execute ${arr_cmds[$i]}'";
    sleep 1
done


echo "Sleeping for 5 seconds..."
sleep 5

echo "ASSUME LEADER IS STILL MASTER_PORT"
echo "Kill leader node on port $MASTER_PORT"
kill -9 $(lsof -t -i:$MASTER_PORT)

echo "Kill another node on port $(( MASTER_PORT + 1 ))"
kill -9 $(lsof -t -i:$(( MASTER_PORT + 1 )))

NUM_NODES=$(( NUM_NODES - 2 ))
MASTER_PORT=$(( MASTER_PORT + 2 ))
NUM_FOLLOWERS=$(( NUM_NODES - 1 ))

echo "Sleeping for 5 seconds..."
sleep 5

arr_cmds2=(
    'dequeue()', 'dequeue()', 
    'dequeue()', 'queue("t")', 
    'queue("e")', 'queue("r")')

echo "Sending commands to nodes..."

for (( i=0; i<${#arr_cmds2[@]}; i++ ))
do
    echo "Sending command ${arr_cmds2[$i]} to node $i on port $MASTER_PORT"
    gnome-terminal --tab --title="client$i" -e "sh -c 'python3 one_cmd_client.py localhost $MASTER_PORT execute ${arr_cmds2[$i]}'";
    sleep 1
done

echo "Sleeping for 3 seconds..."
sleep 3

PORT=$(( MASTER_PORT - 1 ))
echo "Restarting node on port $PORT"
gnome-terminal --tab --title="server$i" -e "sh -c 'python3 server.py localhost $PORT localhost $MASTER_PORT'";

echo "Sleeping for 2 seconds..."
sleep 2

PORT=$(( MASTER_PORT - 2 ))
echo "Restarting node on port $PORT"
gnome-terminal --tab --title="server$i" -e "sh -c 'python3 server.py localhost $PORT localhost $MASTER_PORT'";

echo "Sleeping for 2 seconds..."
sleep 2

arr_cmds3=(
    'queue("U")', 'queue("w")', 
    'queue("U")')

echo "Sending commands to nodes..."

PORT=$(( MASTER_PORT - 2 ))
for (( i=0; i<${#arr_cmds3[@]}; i++ ))
do
    echo "Sending command ${arr_cmds3[$i]} to node $i on port $PORT"
    gnome-terminal --tab --title="client$i" -e "sh -c 'python3 one_cmd_client.py localhost $PORT execute ${arr_cmds3[$i]}'";
    sleep 1
done

echo "Sleeping for 5 seconds..."
sleep 5

# REQUEST LOGS
gnome-terminal --tab --title="client" -e "sh -c 'python3 one_cmd_client.py localhost $MASTER_PORT request_log'";

tc qdisc del dev lo root netem delay 1000ms 50ms reorder 8% corrupt 5% duplicate 2% 5% loss 5%
