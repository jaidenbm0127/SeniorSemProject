import os
import re
import subprocess
import threading
import time
import pandas as pd
import matplotlib.pyplot as plt
from PerformanceMonitoring.processor import get_processes

keep_going = True


def graph_results(servers, results):
    print("Making results... ")
    # Create a pandas DataFrame from the results
    df = pd.DataFrame(results)

    # Group the results by server and protocol, and calculate the mean of each metric
    grouped = df.groupby(["server", "protocol"]).mean()

    # Create a multi-index DataFrame with each metric as a column
    metrics = ["download", "upload", "packet_loss", "latency"]
    multi_index = pd.MultiIndex.from_product([servers, ["wireguard", "openvpn"]], names=["server", "protocol"])
    metric_df = pd.DataFrame(columns=metrics, index=multi_index)

    # Fill in the metric DataFrame with the grouped results
    for index, row in grouped.iterrows():
        metric_df.loc[(index[0], index[1]), "download"] = row["download"]
        metric_df.loc[(index[0], index[1]), "upload"] = row["upload"]
        metric_df.loc[(index[0], index[1]), "packet_loss"] = row["packet_loss"]
        metric_df.loc[(index[0], index[1]), "latency"] = row["latency"]

    # Convert the metric DataFrame to a wide format
    wide_df = metric_df.unstack()

    # Create a bar plot of the metrics for each server
    fig, axs = plt.subplots(nrows=len(servers), ncols=len(metrics), figsize=(15, 15), sharex=True, sharey="row")

    for i, server in enumerate(servers):
        for j, metric in enumerate(metrics):
            axs[i, j].bar(["WireGuard", "OpenVPN"],
                          [wide_df.loc[server, metric]["wireguard"], wide_df.loc[server, metric]["openvpn"]])
            axs[i, j].set_title(f"{metric} - {server}")

    plt.tight_layout()
    plt.show()


def run_mullvad_speedtest(server, protocol):
    # Select a server
    cmd = f"mullvad relay set location {server}"
    subprocess.run(cmd, shell=True, capture_output=True, text=True)

    cmd = f"mullvad relay set tunnel-protocol {protocol}"
    subprocess.run(cmd, shell=True, capture_output=True, text=True)

    # Connect to the server
    cmd = "mullvad connect"
    subprocess.run(cmd, shell=True, capture_output=True, text=True)

    # Wait for the connection to stabilize
    time.sleep(5)

    print("Running speedtest")
    resources_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Resources")
    exe_path = os.path.join(resources_path, "speedtest.exe")
    output = subprocess.check_output([exe_path]).decode()

    print(output)

    # Extract download speed
    download_speed_match = re.search(r"Download:\s+([\d\.]+)\s+Mbps", output)
    download_speed = float(download_speed_match.group(1))

    # Extract upload speed
    upload_speed_match = re.search(r"Upload:\s+([\d\.]+)\s+Mbps", output)
    upload_speed = float(upload_speed_match.group(1))

    # Extract idle latency
    idle_latency_match = re.search(r"Idle Latency:\s+([\d\.]+)\s+ms", output)
    idle_latency = float(idle_latency_match.group(1))

    # Extract packet loss
    packet_loss_match = re.search(r"Packet Loss:\s+([\d\.]+)%", output)
    try:
        packet_loss = float(packet_loss_match.group(1))
        return {"server": server, "protocol": protocol, "download": download_speed, "upload": upload_speed,
                "packet_loss": packet_loss,
                "latency": idle_latency}
    except AttributeError:
        print("Running again, AttributeError")
        return run_mullvad_speedtest(server, protocol)


def mullvad():
    print("Starting Mullvad daemon... ")

    # Sign in to Mullvad using the CLI tool
    username = "1573666943771546"
    cmd = f"mullvad account login {username}"
    subprocess.run(cmd, shell=True, capture_output=True, text=True)

    mullvad_servers = ["us nyc", "us dal", "us atl", "us lax", "us mia", "us sea", "jp tyo", "au mel", "de fra", "gb "
                                                                                                                 "lon"]

    mullvad_thread = threading.Thread(target=collect_data, args=("Mullvad", "mullvad-daemon.exe", "wireguard",))
    mullvad_thread.daemon = True
    mullvad_thread.start()

    # Start a separate thread for each server
    results = []
    print("Testing Mullvad WireGuard... ")
    for server in mullvad_servers:
        results.append(run_mullvad_speedtest(server, "wireguard"))
        print(results)
        # Disconnect from the server
        cmd = "mullvad disconnect"
        subprocess.run(cmd, shell=True, capture_output=True, text=True)

        time.sleep(5)

    global keep_going
    keep_going = False
    print("Joining Logging thread... ")
    mullvad_thread.join()

    keep_going = True

    mullvad_thread = threading.Thread(target=collect_data, args=("Mullvad", "mullvad-daemon.exe", "openvpn",))
    mullvad_thread.daemon = True
    mullvad_thread.start()

    print("Testing Mullvad OpenVPN... ")
    for server in mullvad_servers:
        results.append(run_mullvad_speedtest(server, "openvpn"))
        print(results)
        # Disconnect from the server
        cmd = "mullvad disconnect"
        subprocess.run(cmd, shell=True, capture_output=True, text=True)

        time.sleep(5)

    keep_going = False
    print("Joining Logging thread... ")
    mullvad_thread.join()

    graph_results(mullvad_servers, results)

    cmd = "mullvad disconnect"
    subprocess.run(cmd, shell=True, capture_output=True, text=True)


def run_ivpn_speedtest(server, protocol):
    # Connect to server while selecting server and protocl
    cmd = f"ivpn connect -p {protocol} -city -any -fastest {server}"
    subprocess.run(cmd, shell=True, capture_output=True, text=True)

    # Wait for the connection to stabilize
    time.sleep(5)

    print("Running speedtest")
    resources_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Resources")
    exe_path = os.path.join(resources_path, "speedtest.exe")
    output = subprocess.check_output([exe_path]).decode()

    print(output)

    # Extract download speed
    download_speed_match = re.search(r"Download:\s+([\d\.]+)\s+Mbps", output)
    download_speed = float(download_speed_match.group(1))

    # Extract upload speed
    upload_speed_match = re.search(r"Upload:\s+([\d\.]+)\s+Mbps", output)
    upload_speed = float(upload_speed_match.group(1))

    # Extract latency
    latency_match = re.search(r"Latency:\s+([\d\.]+)\s+ms", output)
    latency = float(latency_match.group(1))

    # Extract packet loss
    packet_loss_match = re.search(r"Packet Loss:\s+([\d\.]+)%", output)
    try:
        packet_loss = float(packet_loss_match.group(1))
        return {"server": server, "protocol": protocol, "download": download_speed, "upload": upload_speed,
                "packet_loss": packet_loss,
                "latency": latency}
    except AttributeError:
        print("Running again, AttributeError")
        return run_ivpn_speedtest(server, protocol)


def ivpn():
    print("Starting IVPN daemon... ")

    username = "i-J8EQ-5HD8-2V8G"
    cmd = f"ivpn login {username}"
    subprocess.run(cmd, shell=True, capture_output=True, text=True)

    ivpn_servers = ["ny", "dallas", "atlana", "angeles", "miami", "seattle", "tokyo", "sydney", "frankfurt", "london"]

    ivpn_thread = threading.Thread(target=collect_data, args=("IVPN", "wireguard.exe", "wireguard",))
    ivpn_thread.daemon = True
    ivpn_thread.start()

    # Start a separate thread for each server
    results = []
    print("Testing IVPN WireGuard... ")
    for server in ivpn_servers:
        results.append(run_ivpn_speedtest(server, "wireguard"))

        print(results)
        # Disconnect from the server
        cmd = "ivpn disconnect"
        subprocess.run(cmd, shell=True, capture_output=True, text=True)

        time.sleep(5)

    global keep_going
    keep_going = False
    print("Joining Logging thread... ")
    ivpn_thread.join()

    keep_going = True

    ivpn_thread = threading.Thread(target=collect_data, args=("IVPN", "openvpn.exe", "openvpn",))
    ivpn_thread.daemon = True
    ivpn_thread.start()

    print("Testing IVPN OpenVPN... ")
    for server in ivpn_servers:
        results.append(run_ivpn_speedtest(server, "openvpn"))
        print(results)
        # Disconnect from the server
        cmd = "ivpn disconnect"
        subprocess.run(cmd, shell=True, capture_output=True, text=True)

        time.sleep(5)

    keep_going = False
    print("Joining Logging thread... ")
    ivpn_thread.join()

    graph_results(ivpn_servers, results)

    cmd = "ivpn disconnect"
    subprocess.run(cmd, shell=True, capture_output=True, text=True)


def collect_data(vpn_provider_name, vpn_exe_name, protocol, vpn_alt_exe_name=None):
    with open(f"{vpn_provider_name}_{protocol}.txt", 'w') as f:
        while keep_going:
            process = get_processes(vpn_exe_name, vpn_alt_exe_name)
            if process is not None:
                row = f"{process.process_cpu},{process.process_memory}\n"
                f.write(row)


def main():
    print("Starting main method now.")
    mullvad()
    ivpn()


if __name__ == "__main__":
    main()
