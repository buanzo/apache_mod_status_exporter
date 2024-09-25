#!/usr/bin/env python3.10
import os
import configparser
import asyncio
import aiohttp
import argparse
from prometheus_client import start_http_server, Gauge
from urllib.parse import urlparse, parse_qs, urlunparse
import time

# Define Prometheus metrics globally (not specific to a single server)
apache_total_accesses = Gauge('apache_total_accesses', 'Total number of accesses', ['hostname'])
apache_cpu_load = Gauge('apache_cpu_load', 'CPU load', ['hostname'])
apache_uptime = Gauge('apache_uptime', 'Uptime in seconds', ['hostname'])
apache_req_per_sec = Gauge('apache_req_per_sec', 'Requests per second', ['hostname'])
apache_bytes_per_sec = Gauge('apache_bytes_per_sec', 'Bytes transferred per second', ['hostname'])
apache_worker_ratio = Gauge('apache_worker_ratio', 'Ratio of busy to idle workers', ['hostname'])
apache_busy_workers = Gauge('apache_busy_workers', 'Number of busy workers', ['hostname'])
apache_idle_workers = Gauge('apache_idle_workers', 'Number of idle workers', ['hostname'])

# Function to ensure the 'auto' parameter is present in the URL
def ensure_auto_parameter(url):
    """
    Ensures that the URL contains the 'auto' parameter for Apache server status.
    """
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    if 'auto' not in query_params:
        new_query = parsed_url.query
        if new_query:
            new_query += '&auto'
        else:
            new_query = 'auto'
        new_url_parts = parsed_url._replace(query=new_query)
        return urlunparse(new_url_parts)
    return url

# Asynchronous function to fetch Apache status from a URL
async def fetch_apache_status(session, url, http_proxy=None, https_proxy=None):
    """
    Fetches Apache server status from the given URL, using the specified HTTP and HTTPS proxies if defined.
    """
    # Set proxies if defined
    proxies = {}
    if http_proxy is not None:
        proxies['http'] = http_proxy
        os.environ['http_proxy'] = http_proxy
    if https_proxy is not None:
        proxies['https'] = https_proxy
        os.environ['https_proxy'] = https_proxy

    async with session.get(url, proxy=proxies.get('http')) as response:
        response.raise_for_status()
        server_status = {}
        data = await response.text()
        # Parse the server status information into a dictionary
        for item in data.split('\n'):
            splitted = item.split(': ')
            if len(splitted) == 2:
                key, val = splitted
                server_status[key.strip()] = val.strip()
        return server_status

# Update Prometheus metrics for each server with the appropriate labels
def update_metrics(server_label, server_status, verbose):
    """
    Updates the Prometheus metrics based on the Apache server status for a given server label.
    """
    if verbose:
        print(f'Updating server metrics for {server_label}')
    apache_total_accesses.labels(hostname=server_label).set(float(server_status.get('Total Accesses', 0)))
    apache_cpu_load.labels(hostname=server_label).set(float(server_status.get('CPULoad', 0)))
    apache_uptime.labels(hostname=server_label).set(float(server_status.get('Uptime', 0)))
    apache_req_per_sec.labels(hostname=server_label).set(float(server_status.get('ReqPerSec', 0)))
    apache_bytes_per_sec.labels(hostname=server_label).set(float(server_status.get('BytesPerSec', 0)))

    # Retrieve worker statistics and update metrics
    busy_workers = int(server_status.get('BusyWorkers', 0))
    idle_workers = int(server_status.get('IdleWorkers', 0))
    apache_busy_workers.labels(hostname=server_label).set(busy_workers)
    apache_idle_workers.labels(hostname=server_label).set(idle_workers)

    # Calculate and set the worker ratio (busy/idle)
    if idle_workers > 0:
        ratio = busy_workers / idle_workers
    else:
        ratio = busy_workers  # Default to busy workers if no idle workers are present
    apache_worker_ratio.labels(hostname=server_label).set(ratio)

# Asynchronous task to collect metrics for all configured servers
async def collect_metrics(config, global_http_proxy, global_https_proxy, verbose):
    """
    Collects metrics for all servers defined in the configuration file, applying global or server-specific proxy settings.
    """
    async with aiohttp.ClientSession() as session:
        tasks = []
        for server_label in config.sections():
            if server_label == "config":  # Skip the global config section
                continue
            url = ensure_auto_parameter(config[server_label]['url'])
            # Use server-specific proxies if set; otherwise, fallback to global proxies
            server_http_proxy = config[server_label].get('http_proxy', global_http_proxy)
            server_https_proxy = config[server_label].get('https_proxy', global_https_proxy)
            task = asyncio.create_task(fetch_and_update(session, server_label, url, server_http_proxy, server_https_proxy, verbose))
            tasks.append(task)
        await asyncio.gather(*tasks)

# Fetch the status and update the metrics for a single server
async def fetch_and_update(session, server_label, url, http_proxy, https_proxy, verbose):
    """
    Fetches the Apache status for a specific server and updates the corresponding metrics.
    """
    try:
        server_status = await fetch_apache_status(session, url, http_proxy, https_proxy)
        update_metrics(server_label, server_status, verbose)
    except Exception as e:
        print(f"Error fetching data from {server_label}: {e}")

def main():
    # Set up argument parsing for command-line options
    parser = argparse.ArgumentParser(description='Apache mod_status exporter for Prometheus')
    parser.add_argument('-c', '--config', default='config.ini', help='Path to the configuration file (default: config.ini)')
    args = parser.parse_args()

    # Load configuration from the specified file
    config = configparser.ConfigParser()
    config.read(args.config)

    # Get the scraping interval from config (default to 300 seconds if not specified)
    scrape_time_delay = int(config['config'].get('scrape_time_delay', 300))

    # Retrieve global proxy settings from the config
    global_http_proxy = config['config'].get('http_proxy', None)
    global_https_proxy = config['config'].get('https_proxy', None)

    # Convert "None" string to actual None if present
    if global_http_proxy == "None":
        global_http_proxy = None
    if global_https_proxy == "None":
        global_https_proxy = None

    # Retrieve verbose setting from the config
    verbose = config['config'].getboolean('verbose', fallback=False)

    print('Starting Prometheus exporter server')
    # Start Prometheus HTTP server on port 9081
    start_http_server(9081, addr="127.0.0.1")

    # Start the metrics collection loop
    print('Starting metrics collection loop')
    while True:
        asyncio.run(collect_metrics(config, global_http_proxy, global_https_proxy, verbose))
        if verbose:
            print(f'Sleeping for {scrape_time_delay} seconds before next collection cycle')
        time.sleep(scrape_time_delay)

if __name__ == "__main__":
    main()
