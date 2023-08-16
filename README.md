# ICON2-docker

#### Welcome to the ICON2-docker github repository.

## Prerequisites

We recommend running nodes using Docker. <br>
Install Docker Engine: [Install Docker Engine](https://docs.docker.com/engine/install/) <br>
Install Docker Compose: [Install Docker Compose](https://docs.docker.com/compose/install/) <br>
Official Docker Image:  `iconloop/icon2-node`


```
System Requirements 

CPU:  minimum 4core, recommend 8core +
RAM:  minimum 16GB, recommend 32GB + 
DISK : minimum SSD 1.5TB, recommend SSD 2TB + 
Network: minimum 1Gbps, recommend 2Gbps +

External Communications 
TCP 7100: TCP port used for peer-to-peer connection between peer nodes.
TCP 9000: JSON-RPC or RESTful API port serving application requests.P-Rep must allow TCP connections to port 7100 and 9000 of an external host. ( Use 0.0.0.0/0 for a source from any network )
```

## Getting started

Open docker-compose.yml in a text editor and add the following content:

```yaml
version: "3"
services:
   prep:
      image: iconloop/icon2-node
      container_name: "icon2-node"
      network_mode: host
      restart: "on-failure"
      environment:
         SERVICE: "MainNet"  # MainNet, LisbonNet, BerlinNet   ## kind of network type 
         GOLOOP_LOG_LEVEL: "debug" # trace, debug, info, warn, error, fatal, panic          
         KEY_STORE_FILENAME: "INPUT_YOUR_KEY_STORE_FILENAME" # e.g. keystore.json read a config/keystore.json
         # e.g. "/goloop/config/keystore.json" read a "config/keystore.json" of host machine
         KEY_PASSWORD: "INPUT_YOUR_KEY_PASSWORD"
         FASTEST_START: "true"    # It can be restored from latest Snapshot DB.
         ROLE: 3 # preps = 3, citizen = 0

      cap_add:
         - SYS_TIME

      volumes:         
         - ./data:/goloop/data # mount a data volumes
         - ./config:/goloop/config # mount a config volumes ,Put your used keystore file here.     
         - ./logs:/goloop/logs

```


Start up

```yaml
$ docker-compose pull && docker-compose up -d
```





To see the logs of the ICON2 node you can execute

```
$ tail -f logs/booting.log


$ tail -f logs/goloop.log
```


The directories(data, config, icon, logs …) are created by docker engine, but config directory needs to importing your keystore file.

```
.
├── docker-compose.yml 
├── config               # configuration files                         
│   └── keystore.json   # Import the your keystore file

├── data                # block data
│   ├── 1
│   ├── auth.json
│   ├── cli.sock
│   ├── ee.sock
│   └── rconfig.json

├── icon   # icon1 data for migrate. If a migration is completed, it will be auto-remove
│   └── migrator_bm
└── logs   # log files
    ├── booting.log   
    ├── health.log    # health state log
    ├── chain.log     # goloop chain action logs
    ├── download.log
    ├── download_error.log # download  
    └── goloop.log   # goloop's log file
```




## Docker environments settings

| Name               | default                | type | required | description                                                                      |
|--------------------|------------------------|------|----------|----------------------------------------------------------------------------------|
| SERVICE            | MainNet                | str  | false    | Service Name - (MainNet, LisbonNet, BerlinNet)                                   |
| ROLE               | 0                      | int  | true     | Role of running node. 0: Citizen, 3: P-Rep                                       |
| CONFIG_URL         |                        | str  | false    |                                                                                  |
| CONFIG_URL_FILE    | default_configure.json | str  | false    |                                                                                  |
| CONFIG_LOCAL_FILE  | configure.json         | str  | false    |                                                                                  |
| IS_AUTOGEN_CERT    | false                  | bool | false    | Automatically generate certificates                                              |
| FASTEST_START      | false                  | bool | false    | Download snapshot DB                                                             |
| KEY_STORE_FILENAME | keystore.json          | str  | true     | keystore.json file name                                                          |
| KEY_PASSWORD       |                        | str  | true     | password of keystore.json file                                                   |
| USE_NTP_SYNC       | True                   | bool | false    | Whether to use NTP in container                                                  |
| NTP_SERVER         |                        | str  | false    | NTP Server                                                                       |
| NTP_REFRESH_TIME   |                        | int  | false    | ntp refresh time                                                                 |
| SLACK_WH_URL       |                        | str  | false    | slack web hook url - If a problem occurs, you can receive an alarm with a slack. |
| USE_HEALTH_CHECK   | True                   | bool | false    | Whether to use health check                                                      |
| CHECK_TIMEOUT      | 10                     | int  | false    | sec - TIMEOUT when calling REST API for monitoring                               |
| CHECK_PEER_STACK   | 6                      | int  | false    | sec - Stack value to check the peer for monitoring.                              |
| CHECK_BLOCK_STACK  | 10                     | int  | false    | sec - Stack value to check the block for monitoring.                             |
| CHECK_INTERVAL     | 10                     | int  | false    | sec - check interval for monitoring                                              |
| CHECK_STACK_LIMIT  | 360                    | int  | false    | count - count- Restart container when stack value is reached                     |
| GOLOOP_LOG_LEVEL   | debug                  | str  | false    | Log Level - (trace,debug,info,warn,error,fatal,panic                             |       
| LOG_OUTPUT_TYPE    | file                   | str  | false    | sec - check interval for monitoring                                              |
