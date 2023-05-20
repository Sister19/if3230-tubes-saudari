import { useState, useEffect } from 'react'
import { IClusterElmt, INodeStatus } from './types'
import axios from 'axios'

function App() {
  const [nodeStatus, setNodeStatus] = useState<INodeStatus[]>([])
  const [ip, setIp] = useState<string>('localhost');
  const [port, setPort] = useState<number>(5000);
  const [continous, setContinous] = useState<boolean>(false);

  const fetchNodeStatus = async () => {
    try {
      const res = await axios.get<INodeStatus[]>(`http://localhost:8080/cluster?ip=${ip}&port=${port}`)
      console.log(res.data)
      setNodeStatus(res.data)
    } catch (err) {
      console.log(err)
      alert(err)
      setNodeStatus([])
    }
  }

  useEffect(() => {
    if (continous) {
      const interval = setInterval(() => {
        fetchNodeStatus()
      }, 1000)

      return () => clearInterval(interval)
    } else {
      fetchNodeStatus()
    }
  }, [continous])

  return (
    <div>
      <div>
        <div>
          <label htmlFor="ip">IP: </label>
          <input type="text" id="ip" value={ip} onChange={(e) => setIp(e.target.value)} />

          <label htmlFor="port">Port: </label>
          <input type="number" id="port" value={port} onChange={(e) => setPort(parseInt(e.target.value))} />

          <label htmlFor="continous"></label>
          <input type="checkbox" id="continous" checked={continous} onChange={(e) => setContinous(
            e.target.checked
          )} />
        </div>
        <div>
          <button onClick={() => {
            fetchNodeStatus()
          }}>
            Fetch
          </button>
        </div>
      </div>

      <div>
        {
          nodeStatus.map((status) => {
            return (
              <div key={`${status.address.ip}:${status.address.port}`}>
                <h3>Address: {status.address.ip}:{status.address.port}</h3>
                <div>
                  <table>
                    <thead>
                      <tr>
                        <th>Current Term</th>
                        <th>Voted For</th>
                        <th>Commit Length</th>
                        <th>Type</th>
                        <th>Cluster Leader Addr</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>{status.election_term}</td>
                        <td>{JSON.stringify(status.voted_for)}</td>
                        <td>{status.commit_length}</td>
                        <td>{status.type}</td>
                        <td>{JSON.stringify(status.cluster_leader_addr)}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div>
                  <p>Log:</p>
                  <div>
                    <table>
                      <thead>
                        <tr>
                          <th>Term</th>
                          <th>Command</th>
                          <th>Value</th>
                        </tr>
                      </thead>
                      <tbody>
                        {status.log.map(log => {
                          return (
                            <tr key={JSON.stringify(log)}>
                              <td>{log.term}</td>
                              <td>
                                {log.command}
                              </td>
                              <td>
                                {log.value}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
                <p>
                  Votes Received: {JSON.stringify(status.votes_received)}
                </p>
                <div>
                  <p>Cluster Elmts</p>
                  <table>
                    <thead>
                      <tr>
                        <th>Key</th>
                        <th>Address</th>
                        <th>Sent Length</th>
                        <th>Acked Length</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.keys(status.cluster_elmts).map((key) => {
                        const data = status.cluster_elmts[key as keyof IClusterElmt]

                        return (
                          <tr key={key}>
                            <td>{key}</td>
                            <td>{data.addr.ip}:{data.addr.port}</td>
                            <td>{data.sent_length}</td>
                            <td>{data.acked_length}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })
        }
      </div>
    </div>
  )
}

export default App
