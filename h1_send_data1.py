from scapy.all import Ether,IP, ICMP, send,Raw

# 创建一个 ICMP 请求数据包
#"/"斜杠是用来连接不同层的数据包，它将 IP 层和 ICMP 层连接在一起，形成一个完整的数据包。
packet = IP(src="10.0.0.1",dst='10.0.0.4')/ ICMP()/Raw(load="content 1")


# 发送数据包到指定目标
send(packet)