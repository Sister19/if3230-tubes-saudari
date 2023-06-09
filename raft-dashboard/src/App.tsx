import { useState, useEffect } from 'react'
import { IClusterElmt, INodeStatus } from './types'
import axios, {AxiosError} from 'axios'
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

function App() {
  const [nodeStatus, setNodeStatus] = useState<INodeStatus[]>([])
  const [ip, setIp] = useState<string>('localhost');
  const [port, setPort] = useState<number>(5002);
  const [continous, setContinous] = useState<boolean>(false);
  const [delay, setDelay] = useState<number>(1000);

  const fetchNodeStatus = async () => {
    try {
      const res = await axios.get<INodeStatus[]>(`http://localhost:8080/cluster?ip=${ip}&port=${port}`)
      console.log(res.data)
      setNodeStatus(res.data)
    } catch (err) {
      console.log(err)
      const msg = (err as AxiosError).message
      toast(msg)
      setNodeStatus([])
    }
  }

  useEffect(() => {
    if (continous) {
      const interval = setInterval(() => {
        fetchNodeStatus()
      }, delay)

      return () => clearInterval(interval)
    } else {
      fetchNodeStatus()
    }
  }, [continous, ip, port, delay])

  return (
    <div>
      <ToastContainer />
      <div>
        <div>
          <label htmlFor="ip">IP: </label>
          <input type="text" id="ip" value={ip} onChange={(e) => setIp(e.target.value)} />

          <label htmlFor="port">Port: </label>
          <input type="number" id="port" value={port} onChange={(e) => setPort(parseInt(e.target.value))} />

          <label htmlFor="delay">Delay</label>
          <input type="number" id="delay" value={delay} onChange={(e) => setDelay(parseInt(e.target.value))} />

          <label htmlFor="continous">Continous: </label>
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
                <div>
                  <p>
                    App Data: {
                      JSON.stringify(status.app_data)
                    }
                  </p>
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
