from scapy.all import sniff, ICMP,IP

# 定义回调函数来处理捕获的数据包
def packet_callback(packet):
    if ICMP in packet:
        print("Received ICMP packet from h1.")

# 监听网络接口
sniff(filter="icmp", prn=packet_callback, store=0)
