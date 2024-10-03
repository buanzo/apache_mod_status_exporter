# Apache mod_status Exporter for Prometheus

This script is an Apache `mod_status` exporter for Prometheus. It collects Apache server metrics such as total accesses, CPU load, uptime, requests per second, and worker statistics (busy and idle workers) and exposes them to Prometheus.

## Features

- Collects metrics from multiple Apache servers using `mod_status`.
- Supports configuration of global and per-server proxy settings.
- Exposes collected metrics to Prometheus on a specified port.
- Configurable scraping intervals.
- Verbose logging option for detailed output.

## Requirements

- Python 3.10 or higher
- `aiohttp` library
- `prometheus_client` library

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/buanzo/apache_mod_status_exporter
    cd apache_mod_status_exporter
    ```

2. Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1. Copy the sample configuration file `config.sample.ini` to `config.ini`:

    ```bash
    cp config.sample.ini config.ini
    ```

2. Edit `config.ini` to configure your server settings:

    - **`verbose`**: Set to `true` to enable detailed logging; set to `false` to disable.
    - **`scrape_time_delay`**: Interval in seconds between scraping metrics from the servers.
    - **`http_proxy` / `https_proxy`**: Set global proxy settings for all servers. Use `None` if no proxy is required.
    - Add individual server sections to configure URLs and override proxy settings if necessary.

### Example `config.ini`

```ini
[config]
verbose = false
scrape_time_delay = 300
# You can specify a global proxy setting, and override per host
http_proxy = None
https_proxy = None

[localhost]
url = http://localhost/server-status

[remote_server]
url = https://example.com/server-status
# Optional: custom proxy for this server
http_proxy = http://custom-proxy:8080
https_proxy = http://custom-proxy:8080
```

## Usage

Run the exporter with the specified configuration file:

```bash
python apache_mod_status_exporter.py -c config.ini
```

### Command-line Options

- `-c`, `--config`: Path to the configuration file (default: `config.ini`).

## Metrics Collected

The exporter collects the following metrics from Apache:

- `apache_total_accesses`: Total number of accesses.
- `apache_cpu_load`: CPU load.
- `apache_uptime`: Uptime in seconds.
- `apache_req_per_sec`: Requests per second.
- `apache_bytes_per_sec`: Bytes transferred per second.
- `apache_worker_ratio`: Ratio of busy to idle workers (custom, calculated by the exporter).
- `apache_busy_workers`: Number of busy workers.
- `apache_idle_workers`: Number of idle workers.

## Running the Exporter

Once started, the exporter runs a local HTTP server on port 9081 to expose the collected metrics to Prometheus. Make sure your Prometheus configuration includes the exporter endpoint:

```yaml
scrape_configs:
  - job_name: 'apache_mod_status_exporter'
    static_configs:
      - targets: ['localhost:9081']
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Feel free to submit issues or pull requests if you find bugs or have suggestions for improvements.

## Acknowledgments

- This script uses `aiohttp` for asynchronous HTTP requests and `prometheus_client` for exposing metrics to Prometheus.
