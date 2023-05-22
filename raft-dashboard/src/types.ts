export interface IAddress {
    ip: string;
    port: number;
}

export interface ILog {
    term: number;
    command: string;
    value: string;
}

export interface IClusterElmt {
    addr: IAddress;
    sent_length: number;
    acked_length: number;
}

export interface INodeStatus {
    address: IAddress;
    election_term: number;
    voted_for: IAddress;
    log: ILog[];
    commit_length: number;
    type: string;
    cluster_leader_addr: IAddress;
    votes_received: IAddress[];
    cluster_elmts: {
        [key: string]: IClusterElmt
    }
    app_data: unknown[]
}
