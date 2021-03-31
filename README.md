# Vlan L2 counters exporter for Cisco Nexus switches
Prometheus exporter of vlan L2 counters for NXOS devices.
Netconf ssh service on standart port(830) must be enabled on target device.

### Runnig exporter as a Flask application:

```
export FLASK_APP=nxos-vlan-stat-exporter.py
export DEVICE_USER=username
export DEVICE_PASSWORD=password
/usr/bin/env python3 -m flask run --host=0.0.0.0 --port=8080
```

Username and password should be defined in environment variables or in .env file:

### Running exporter in docker:
```
docker run -d -e DEVICE_USER=username -e DEVICE_PASSWORD=password\
  -p 8080:8080 --name nxos-vlan-stat-exporter kvitex/nxos-vlan-stat-exporter
```

or

```
docker run --env-file .env -p 8080:8080 --name nxos-vlan-stat-exporter kvitex/nxos-vlan-stat-exporter
```

### Prometheus job example

Static configuration:

```
scrape_configs:
  - job_name: route_stat
    scrape_interval: 5m
    scrape_timeout: 3m
    metrics_path: /metrics
    static_configs:
      - targets:
        - 10.10.10.1
        - 10.10.10.2
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_hostname
      - source_labels: [__param_hostname]
        target_label: instance
      - target_label: __address__
        replacement: my_host_address:8080
```

Or you can use file service discovery:

```
scrape_configs:
  - job_name: route_stat
    scrape_interval: 5m
    scrape_timeout: 3m
    metrics_path: /metrics
    file_sd_configs:
      - files:
        - vlan_stat_*.yml
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_hostname
      - source_labels: [__param_hostname]
        target_label: instance
      - target_label: __address__
        replacement: my_host_address:8080
```

vlan_stat_static.yml

```
- labels:
    router: "BORDER-1"
  targets:
    - 10.10.10.1
- labels:
    router: "BORDER-2"
  targets:
    - 10.10.10.2
```

### Todos

 - Add per target netconf port customization 
 

