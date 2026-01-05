# Orbit-5G Base Station Troubleshooting Manual
**OS Version:** NebulaOS v4.2 LTS  
**Document ID:** ORB-TRBL-2023-A4  
**Classification:** Internal Technical Reference

---

## 1. Hardware Alarms

### HW-1002: BBU Power Rail Instability
*   **Description**: The Baseband Unit (BBU) DC-DC converter has detected voltage fluctuations exceeding ±5% tolerance on the 48V rail. This usually indicates a failing PSU module or site power rectifier instability.
*   **Resolution Procedure**:
    1.  Using a multimeter, measure the input voltage at the BBU terminal block `TB-PWR-MAIN`. Ensure reading is between -40.5V DC and -57V DC.
    2.  Check the site rectifier logs for "Rectifier Module Fail" or "Mains Low Voltage" events.
    3.  If site power is stable, inspect the Orbit-5G PSU LED status. A blinking amber LED indicates a localized capacitor fault.
    4.  Perform a hot-swap of the BBU Power Supply Unit (PSU-A or PSU-B).
    5.  Reset the alarm via the physical Reset button held for 5 seconds or via CLI: `nebula-cli hw clear-alarm HW-1002`.

### HW-2045: RRU Optical Module LOS (Loss of Signal)
*   **Description**: The Remote Radio Unit (RRU) on Sector 2 is not receiving optical light from the SFP+ transceiver. This severs the CPRI/eCPRI link between the BBU and the radio head.
*   **Resolution Procedure**:
    1.  Verify the physical fiber connection at port `SFP-2` on the BBU and the corresponding RRU port.
    2.  Use an Optical Power Meter (OPM) to measure Rx power at the BBU side. Acceptable range is -3 dBm to -14 dBm.
    3.  Inspect the fiber ferrule using a fiberscope; clean using a click-cleaner if dust particles are detected.
    4.  Replace the SFP+ transceiver module (Part #ORB-SFP-25G) if the Rx power remains below -30 dBm (dark).
    5.  Run a loopback test to verify the port logic: `nebula-cli phy --port sfp2 --loopback internal`.

### HW-3011: GNSS Antenna Short Circuit
*   **Description**: The GNSS receiver chip detects zero resistance or a short circuit on the coaxial feed line. This prevents the base station from acquiring PTP (Precision Time Protocol) phase synchronization.
*   **Resolution Procedure**:
    1.  Disconnect the coaxial cable from the `GNSS-IN` SMA port.
    2.  Measure the resistance of the cable using an ohmmeter. A reading near 0Ω indicates a short in the cable or the antenna head.
    3.  Measure the voltage output at the `GNSS-IN` port; it should provide 5V DC bias for the active antenna.
    4.  Inspect the surge arrestor installed in the feeder path; replace if the gas tube has tripped.
    5.  Once the cable/antenna is replaced, verify satellite lock: `show clock sync status`.

### HW-4100: FPGA Thermal Critical
*   **Description**: The Field Programmable Gate Array (FPGA) core temperature has exceeded 95°C. The scheduler will throttle throughput to prevent permanent silicon damage.
*   **Resolution Procedure**:
    1.  Check the BBU Fan Tray unit. Ensure all 4 fans are spinning at >4000 RPM via command `show hardware environment fans`.
    2.  Inspect the air intake filter for dust blockage. Replace filter media (Part #ORB-FLT-AIR) if clogged.
    3.  Verify ambient cabinet temperature is not exceeding 55°C. Check site HVAC systems.
    4.  If airflow is sufficient and ambient temp is low, the heatsink thermal compound may have degraded. Replace the Compute Card (CC-1).
    5.  Monitor temperature normalization: `watch -n 1 'cat /sys/class/thermal/thermal_zone0/temp'`.

### HW-5050: MIMO Antenna VSWR High
*   **Description**: Voltage Standing Wave Ratio (VSWR) on RF Path A exceeds 1.5:1. This indicates a significant impedance mismatch, likely due to water ingress in the jumper cables or a damaged connector at the antenna port.
*   **Resolution Procedure**:
    1.  Execute a TDR (Time Domain Reflectometry) sweep from the NebulaOS CLI to locate the distance to fault: `nebula-cli rf --sector 1 --vswr-sweep`.
    2.  If the fault distance corresponds to the top jumper, inspect the DIN 7/16 or 4.3-10 connectors for loose coupling or weatherproofing tape failure.
    3.  Disconnect the jumper and test the antenna port directly with a site analyzer.
    4.  Re-torque all RF connectors to 25 Nm.
    5.  Recalibrate the RF path: `nebula-cli rf calibrate --path A`.

---

## 2. Software Alarms

### S-101: SCTP Association Failure (X2/Xn)
*   **Description**: The Stream Control Transmission Protocol (SCTP) link to the neighbor base station has failed. Handover functionality (X2 for LTE, Xn for 5G) is disabled.
*   **Resolution Procedure**:
    1.  Verify IP reachability to the neighbor gNodeB IP address: `ping -I vlan200 <neighbor_ip>`.
    2.  Check if the firewall is blocking SCTP port 38423 (Xn) or 36422 (X2).
    3.  Verify the SCTP parameters match the neighbor configuration (Stream count, Heartbeat interval).
    4.  Restart the Xn stack: `systemctl restart nebula-xn-stack`.
    5.  Check logs for detailed reject causes: `tail -f /var/log/nebula/sctp.log | grep "ABORT"`.

### S-304: RRC Connection Setup Congestion
*   **Description**: The cell is rejecting new Radio Resource Control (RRC) requests because the active user count exceeds the license limit or the Physical Uplink Control Channel (PUCCH) resources are exhausted.
*   **Resolution Procedure**:
    1.  Check the current active user count against the license limit: `show license usage`.
    2.  If licensed capacity is sufficient, check PUCCH utilization: `show l1-stats --channel pucch`.
    3.  If PUCCH is saturated, modify the system parameters to decrease the periodic CSI reporting frequency for idle users.
    4.  Offload traffic by adjusting `cellIndividualOffset` (CIO) to push users to neighboring cells.
    5.  Command: `nebula-config set cell.1.load_balancing.force_handover = true`.

### S-505: Handover Execution Timeout
*   **Description**: The source gNodeB sent a Handover Command to the UE, but did not receive a "UE Context Release" from the target gNodeB within timer T304 limits.
*   **Resolution Procedure**:
    1.  Check the integrity of the Xn interface (refer to error S-101).
    2.  Verify that the Target Cell ID and PCI (Physical Cell Identity) are correctly defined in the Neighbor Relation Table (NRT): `show neighbor-relation --cell <target_cell_id>`.
    3.  Increase the T304 timer if the handover target is in a high-latency backhaul area (e.g., microwave link): `set l3-timers t304 1000ms`.
    4.  Analyze drive test logs to ensure the handover hysteresis margin is not set too low (causing ping-pong handovers).
    5.  Flush the ARP cache on the backhaul interface: `ip neigh flush all`.

### S-700: DU-CU F1 Interface Mismatch
*   **Description**: The Distributed Unit (DU) and Centralized Unit (CU) are running incompatible software versions, or there is a configuration mismatch in the F1-C setup request.
*   **Resolution Procedure**:
    1.  Check version compatibility matrix. Both CU and DU must run NebulaOS minor versions within 1 release of each other.
    2.  Verify the F1 IP endpoint configurations: `show interface f1-c`.
    3.  Check the PLMN ID list. The PLMNs broadcasted by the DU must match the PLMNs served by the CU.
    4.  Inspect the SCTP payload in the logs for "Abstract Syntax Error".
    5.  Force a re-provisioning of the DU configuration: `nebula-cli provision --force --target du-local`.

### S-999: Database Integrity Corruption
*   **Description**: The configuration database (SQLite/Redis) on the Orbit-5G controller has detected a checksum error or malformed schema on boot.
*   **Resolution Procedure**:
    1.  Do not reboot the node, as it may fail to come back up.
    2.  Enter maintenance mode immediately: `nebula-cli system maintenance-mode enable`.
    3.  Attempt a database consistency check and repair: `nebula-db-tool --check --repair`.
    4.  If repair fails, restore the configuration from the last known good daily backup: `nebula-backup restore --date <YYYY-MM-DD>`.
    5.  Verify integrity after restore: `nebula-db-tool --verify-checksum`.

---

## 3. Connectivity Issues

### Scenario 1: IPSec Tunnel IKEv2 Negotiation Failure
*   **Description**: The base station cannot establish a secure tunnel to the Security Gateway (SeGW). The connection hangs at "Phase 1". This is usually due to a Pre-Shared Key (PSK) mismatch or certificate invalidity.
*   **Resolution Procedure**:
    1.  Capture IKE traffic on the WAN interface: `tcpdump -i eth0 -n port 500 or port 4500`.
    2.  Review logs for `AUTHENTICATION_FAILED`.
    3.  If using Certificates: Verify the local certificate has not expired (`openssl x509 -in /etc/ipsec.d/certs/local.crt -noout -dates`) and that the CA chain is present.
    4.  If using PSK: Re-enter the key in the secrets file. Ensure no trailing whitespace exists.
    5.  Restart the IPSec daemon: `systemctl restart strongswan`.

### Scenario 2: S1/NG Interface Throughput Degradation
*   **Description**: Users report slow download speeds despite good RF signal strength (RSRP > -80 dBm). Throughput is capped at ~10 Mbps on a Gigabit backhaul.
*   **Resolution Procedure**:
    1.  Check the Ethernet port negotiation speed. Ensure it is established at 1000Mb/Full Duplex, not 100Mb/Half: `ethtool eth0`.
    2.  Check for MTU fragmentation issues. Perform a ping sweep with the "Do Not Fragment" bit set: `ping -M do -s 1472 <gateway_ip>`.
    3.  If packets drop at specific sizes, adjust the MTU on the WAN interface: `ip link set dev eth0 mtu 1400`.
    4.  Check Quality of Service (QoS) mappings. Ensure DSCP tagging for user plane traffic (Expedited Forwarding) is correctly mapped to the priority VLAN.
    5.  Disable Ethernet flow control if the upstream router does not support it.

### Scenario 3: PTP Synchronization Drift (Grandmaster Loss)
*   **Description**: The node has lost connectivity to the PTP Grandmaster clock. The internal oscillator is in "Holdover" mode. If sync is not restored within 4 hours, the cells will lock to prevent interference.
*   **Resolution Procedure**:
    1.  Check the status of the PTP client: `ptp4l_client_status`. Note the "Offset from Master" value.
    2.  Ping the Grandmaster IP with high priority QoS to check for network jitter/latency spikes.
    3.  Verify that the upstream switch is configured as a Transparent Clock (TC) or Boundary Clock (BC) to correct residence time.
    4.  If the primary Master is down, manually force a switch to the secondary PTP Master: `nebula-cli sync set-master <secondary_ip>`.
    5.  As a temporary fix, switch sync source to GNSS if satellite visibility is available: `nebula-cli sync source select gnss`.

### Scenario 4: UE Authentication Failure (Error 5G-MM Cause #27)
*   **Description**: User Equipment (UE) can see the network but cannot attach. The Core Network rejects the attachment with "PLMN not allowed" or "Auth Failure".
*   **Resolution Procedure**:
    1.  Verify the connection between the gNodeB and the AMF (Access and Mobility Management Function).
    2.  Check the MCC/MNC broadcast configuration: `show cell-config plmn-id`. Ensure it matches the core network definition.
    3.  Run a subscriber trace for the specific IMSI attempting connection: `nebula-trace start --imsi <target_imsi>`.
    4.  If the trace shows "SCTP Send Failed" to the AMF, check routing tables for the N2 interface.
    5.  Ensure the Tracking Area Code (TAC) configured on the Orbit-5G matches the TAC defined in the AMF allowed list.

### Scenario 5: DHCP Lease Failure on Management VLAN
*   **Description**: After a reboot, the Orbit-5G Base Station is unreachable via the OAM (Operations, Administration, and Maintenance) IP. The unit failed to acquire an IP from the site router.
*   **Resolution Procedure**:
    1.  Connect a laptop to the `LMT` (Local Maintenance Terminal) ethernet port and access via default IP `192.168.1.1`.
    2.  Check the DHCP client logs: `journalctl -u dhclient`. Look for "DHCPDISCOVER" with no "DHCPOFFER".
    3.  Verify the VLAN tagging on the Management Interface. Command: `cat /etc/sysconfig/network-scripts/ifcfg-vlan100`.
    4.  If the switch port configuration changed, the OAM VLAN ID might be mismatched. Update VLAN ID: `nebula-cli net set-oam-vlan <new_vlan_id>`.
    5.  Static fallback: Assign a static IP temporarily to restore remote connectivity: `ip addr add <static_ip>/24 dev eth0.100`.