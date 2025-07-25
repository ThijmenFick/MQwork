import paho.mqtt.client as mqtt
import threading
import random
import time

class provider:
    def __init__(self, broker, port):
        self.broker = broker
        self.port = port

class network:
    def __init__(self, provider, subnet):
        self.provider = provider
        self.subnet = subnet
        self.own_address = f"255.{random.randint(1, 255)}"
        self.claimed_ips = []
        self.onrequest = None
        self._response_received = threading.Event()
        self._request_event = threading.Event()
        self._request_data = {}
        self._request_target = None
        self._mqtt_client = None
        self._ip_claimed_event = threading.Event()

    def _common_setup(self, client):
        def on_connect(client, userdata, flags, rc):
            print("Connected with result code", rc)
            if rc == 0:
                client.subscribe(self.subnet)
                self._connected_event.set()

        def on_message(client, userdata, msg):
            payload = msg.payload.decode()
            try:
                sender, target, *parts = payload.split()

                if len(parts) == 1 and parts[0] == "PING" and target == self.own_address:
                    print(f"Received PING from {sender}, sending RESPONSE")
                    client.publish(self.subnet, f"{self.own_address} {sender} RESPONSE")

                elif len(parts) == 1 and parts[0] == "RESPONSE" and target == self.own_address:
                    self._response_received.set()

                elif len(parts) >= 2 and parts[0] == "REQUEST":
                    data = ' '.join(parts[1:])
                    if target == self.own_address:
                        print(f"Received REQUEST from {sender}: {data}")
                        if self.onrequest:
                            response = self.onrequest(sender, data)
                            if response is not None:
                                client.publish(self.subnet, f"{self.own_address} {sender} RESPONSE {response}")
                        else:
                            # Default echo behavior
                            client.publish(self.subnet, f"{self.own_address} {sender} RESPONSE {data.upper()}")

                elif len(parts) >= 2 and parts[0] == "RESPONSE":
                    data = ' '.join(parts[1:])
                    if sender == self._request_target and target == self.own_address:
                        print(f"Received RESPONSE from {sender}: {data}")
                        self._request_data["response"] = data
                        self._request_event.set()

            except Exception as e:
                print("Error parsing message:", e)

        client.on_connect = on_connect
        client.on_message = on_message

    def dnsconnect(self):
        client = mqtt.Client()
        self._mqtt_client = client
        self._connected_event = threading.Event()
        self._common_setup(client)

        def scan():
            print(f"Started scanning with temporary address {self.own_address}")
            scanned = set()
            while True:
                while True:
                    target = f"{random.randint(1, 254)}.{random.randint(1, 255)}"
                    if target not in scanned:
                        scanned.add(target)
                        break

                print(f"Pinging {target}")
                self._response_received.clear()
                client.publish(self.subnet, f"{self.own_address} {target} PING")

                if self._response_received.wait(timeout=1.5):
                    print(f"{target} is active, skipping.")
                else:
                    print(f"No response from {target}, claiming it.")
                    self.claimed_ips.append(target)
                    self.own_address = target
                    self._ip_claimed_event.set()
                    return

        client.connect(self.provider.broker, self.provider.port, 60)
        client.loop_start()

        if not self._connected_event.wait(timeout=10):
            raise TimeoutError("MQTT connection timed out")

        print("Connection established. Starting scan...")
        scan_thread = threading.Thread(target=scan)
        scan_thread.start()

        if not self._ip_claimed_event.wait(timeout=15):
            raise TimeoutError("No IP could be claimed in time")

        return self.claimed_ips[-1]

    def staticconnect(self, ip):
        self.own_address = ip
        self._mqtt_client = mqtt.Client()
        self._connected_event = threading.Event()
        self._common_setup(self._mqtt_client)

        self._mqtt_client.connect(self.provider.broker, self.provider.port, 60)
        self._mqtt_client.loop_start()

        if not self._connected_event.wait(timeout=10):
            raise TimeoutError("MQTT static connection timed out")

        print(f"Static connection established. Using IP: {self.own_address}")
        return self.own_address

    def request(self, target_ip, own_ip, data, timeout=5):
        if not self._mqtt_client:
            raise RuntimeError("MQTT client not connected. Call dnsconnect() or staticconnect() first.")

        self._request_event.clear()
        self._request_data.clear()
        self._request_target = target_ip

        msg = f"{own_ip} {target_ip} REQUEST {data}"
        print(f"Sending request: {msg}")
        self._mqtt_client.publish(self.subnet, msg)

        if self._request_event.wait(timeout=timeout):
            return self._request_data.get("response")
        else:
            print("Request timed out.")
            return None
