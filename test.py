from MQwork import MQwork
import time

provider = MQwork.provider("broker.hivemq.com", 1883)
net = MQwork.network(provider, "hamstringbyte")
ip = net.staticconnect("1.1")
print(ip)

def hand(f, d):
    print(f"request from {f}")
    return f"Yes {d}"
net.onrequest = hand



while True:
    pass
