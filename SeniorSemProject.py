import re
import subprocess
import sys
import threading
import time
import pandas as pd
import matplotlib.pyplot as plt


def graph_results(results, servers):
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


def loading_animation():
    while True:
        sys.stdout.write("Testing network... ")
        sys.stdout.flush()
        for i in range(8):
            sys.stdout.write('\r Testing network... [' + ' ' * i + '*' + ' ' * (7 - i) + ']')
            sys.stdout.flush()
            time.sleep(0.1)
        for i in range(7, -1, -1):
            sys.stdout.write('\r Testing network... [' + ' ' * i + '*' + ' ' * (7 - i) + ']')
            sys.stdout.flush()
            time.sleep(0.1)


def run_mullvad_speedtest(server, protocol):
    # Sign in to Mullvad using the CLI tool
    username = "1573666943771546"
    cmd = f"mullvad account login {username}"
    subprocess.run(cmd, shell=True, capture_output=True, text=True)

    # Select a server
    cmd = f"mullvad relay set location {server}"
    subprocess.run(cmd, shell=True, capture_output=True, text=True)

    cmd = f"mullvad relay set tunnel-protocol {protocol}"
    subprocess.run(cmd, shell=True, capture_output=True, text=True)

    # Connect to the server
    cmd = "mullvad connect"
    subprocess.run(cmd, shell=True, capture_output=True, text=True)

    # Wait for the connection to stabilize
    time.sleep(4)

    output = subprocess.check_output(["C:\\Users\\feshhi\\Downloads\\ookla-speedtest-1.2.0-win64\\speedtest"]).decode()

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
    packet_loss = float(packet_loss_match.group(1))

    return {"server": server, "protocol": protocol, "download": download_speed, "upload": upload_speed,
            "packet_loss": packet_loss,
            "latency": idle_latency}


def mullvad():
    # List of servers to test
    servers = ["us nyc", "us dal"]

    # Start a separate thread for each server
    results = []
    for server in servers:
        results.append(run_mullvad_speedtest(server, "wireguard"))
        # Disconnect from the server
        cmd = "mullvad disconnect"
        subprocess.run(cmd, shell=True, capture_output=True, text=True)

        time.sleep(3)

    for server in servers:
        results.append(run_mullvad_speedtest(server, "openvpn"))
        # Disconnect from the server
        cmd = "mullvad disconnect"
        subprocess.run(cmd, shell=True, capture_output=True, text=True)

        time.sleep(3)

    graph_results(results, servers)


def main():
    # Start the loading animation in a separate thread
    loading_thread = threading.Thread(target=loading_animation)
    loading_thread.daemon = True
    loading_thread.start()


if __name__ == "__main__":
    main()
