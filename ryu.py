import random
import pickle  # 用来序列化数据类型
import networkx as nx
from threading import Timer
from ryu.topology import event
from ryu.base import app_manager
from collections import defaultdict
from ryu.controller import ofp_event
from ryu.ofproto import ofproto_v1_3
from ryu.topology.api import get_switch, get_link
from ryu.lib.packet import packet, ethernet, arp, lldp, ipv4, ipv6, ether_types, icmp
from ryu.controller.handler import set_ev_cls, CONFIG_DISPATCHER, MAIN_DISPATCHER


class MyController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(MyController, self).__init__(*args, **kwargs)

        self.action = 0  # 后续未使用的变量?
        self.ip2host = {}  # ip和host的映射
        self.datapaths = {}  # 管理的所有交换机
        self.paths = defaultdict(lambda: defaultdict(list))  # 存储原地址到目的地址的路径
        self.graph = nx.read_gml('my_network.gml')  # 读取网络拓扑结构
        #self.flows = pickle.load(open('flows_500.pkl', 'rb'))
        
        # 初始化ip到host的映射
        for v, data in self.graph.nodes(data=True):
            if data['type'] == 'host':
                self.ip2host[data['ip']] = v

    # 函数意义：
    #       清空对应交换机流表
    # 参数说明：
    #       datapath-Openflow交换机对象，需要清空他的流表项
    def empty_flow_table(self, datapath):
        print('Empty Flow Table')
        ofproto = datapath.ofproto  # 协议对象，包含Openflow协议常量，例如动作类型等信息
        parser = datapath.ofproto_parser  # 解析器对象，包含创建Openflow信息的方式

        match = parser.OFPMatch(in_port=1)  # 创建一个匹配对象，指定匹配条件为输入端口1
        # 创建一个流表修改信息对象，此处为删除流表项信息
        mod = parser.OFPFlowMod(datapath, cookie=0, cookie_mask=0, table_id=0, command=ofproto.OFPFC_DELETE, idle_timeout=0, hard_timeout=0, priority=1, 
                                buffer_id=ofproto.OFPCML_NO_BUFFER,out_port=ofproto.OFPP_ANY, out_group=ofproto.OFPG_ANY, flags=0, match=match, instructions=[])

        datapath.send_msg(mod)  # 发送删除流表项信息

    # 函数意义：
    #       当交换机接收到一个没有匹配流表项的数据包，会触发table-missing flow entry流表项，
    #       然后会将这个数据包发送到控制器
    # 参数说明：
    #       datapath-Openflow交换机对象，需要对其添加table-miss流表项
    def missing_flow_table(self, datapath):
        print('Missing Flow Table')
        ofproto = datapath.ofproto  # 协议对象
        parser = datapath.ofproto_parser  # 解析器对象

        match = parser.OFPMatch()  # 创建一个匹配对象，匹配所有数据包
        # 创建一个动作对象，此处为将数据包发送到控制器的动作
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]

        self.add_flow(datapath, 0, match, actions)  # 向交换机添加流表项，优先级最低

    # 函数意义：
    #       添加流表项
    # 参数说明：
    #       datapath-Openflow交换机对象
    #       priority-流表项的优先级
    #       match-流表项的匹配条件
    #       actions-当数据包匹配流表项时要执行的动作列表
    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto  # 协议对象
        parser = datapath.ofproto_parser  # 解析器对象

        # 创建一个应用动作的指令对象
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        # 创建流表修改信息
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)

        datapath.send_msg(mod)  # 发送流表修改信息

    # 函数意义：
    #       计算路由路径
    # 参数说明：
    #       src-源节点
    #       dst-目的节点
    def get_path(self, src, dst):
        # 检查路径是否已经存储，若未存储才进行计算
        if len(self.paths[src][dst]) == 0:
            self.paths[src][dst] = nx.shortest_path(self.graph, src, dst) # 直接调用networkx中函数计算最短路径

        print('Path %s -> %s: %s' % (src, dst, self.paths[src][dst]))
        return self.paths[src][dst]

    # 触发时机：
    #       在交换机和控制器完成握手时触发，此时控制器正处于配置交换机状态
    # 函数意义：
    #       用于处理Openflow交换机特性事件
    #       一般来说这个函数是用来初始化配置Openflow交换机的
    # 参数说明：
    #       ev-事件对象
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        msg = ev.msg  # 从事件对象中提取消息
        datapath = msg.datapath  # 从消息中提取Openflow交换机对象
        self.datapaths[datapath.id] = datapath  # 存储所发现的交换机对象

        self.missing_flow_table(datapath)  # 一般在握手完成后控制器将table-missing flow entry添加到流表中

    # 触发时机：
    #       在EventOFPPacketIn事件发生时，即当一个Openflow交换机收到一个数据包且没有匹配的流表项时，它会将该数据包发送到控制器时
    #       此时控制器正处于MAIN_DISPATCHER状态下，即交换机与控制器的连接已完全建立，控制器可以对交换机进行正常的控制和管理操作时
    # 函数意义：
    #       用于处理Openflow交换机特性事件
    # 参数说明：
    #       ev-事件对象
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        # 初始化信息
        msg = ev.msg  # 提取信息
        datapath = msg.datapath  # 提取交换机对象
        dpid = datapath.id  # 得到交换机id
        ofproto = datapath.ofproto  # 协议对象
        parser = datapath.ofproto_parser  # 解析器对象
        in_port = msg.match['in_port']  # 消息来的交换机的端口，即数据包进入交换机的端口

        # 解析数据包，提取ARP、IPv4、IPv6、LLDP、ICMP、Ethernet协议的数据包
        pkt = packet.Packet(msg.data)
        arp_pkt = pkt.get_protocol(arp.arp)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
        ipv6_pkt = pkt.get_protocol(ipv6.ipv6)
        lldp_pkt = pkt.get_protocol(lldp.lldp)
        icmp_pkt = pkt.get_protocol(icmp.icmp)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)

        # 初始化动作列表
        actions = []

        # 忽略LLDP和IPv6数据包
        if lldp_pkt:
            return
        if ipv6_pkt:
            return
        
        # 处理ICMP数据包
        if icmp_pkt:
            #处理数据包内容
            request = icmp_pkt.data.data.decode()  # 将ICMP数据包的负载部分解码为字符串
            request = ''.join(filter(str.isdigit, request))  # 将ICMP数据包负载部分的数字过滤出来
            request = int(request)  # 将上述数字将转换为int类型
            print("---icmpdata:",request)

            # 处理转发数据包逻辑
            # 如果请求数据的值[1,49]则将数据包发送到h2
            if (1<=request<=49):
                print("send to 2")
                # 配置s1的流表，将数据包转发到h2
                if datapath.id == 1:
                    # 如果进入端口为eth1，将数据包转发至eth2（-h2）
                    if in_port==1:
                        print("s1----inport:",in_port)
                        actions = [parser.OFPActionOutput(2)]
                        out_port = 2
                    # 如果进入端口为eth2，将数据包转发至eth1（-h1）
                    if in_port==2:
                        print("s1----inport:",in_port)
                        actions = [parser.OFPActionOutput(1)]
                        out_port = 1                    
                    match = parser.OFPMatch(in_port=in_port)  # 创建一个匹配对象，指定匹配条件为上述端口
                    self.add_flow(datapath, 1,match, actions)  # 最终添加流表项
            # 如果请求数据的值[50,100]则将数据包发送到h4
            if (50<=request<=100):
                print("send to 4")
                # 配置s1的流表
                if datapath.id == 1:
                    actions = [parser.OFPActionOutput(10)]  # 将数据包输出端口设置为eth10（-s2）
                    match = parser.OFPMatch(in_port=in_port)  # 创建一个匹配对象，指定匹配条件为上述端口
                    self.add_flow(datapath, 1,match, actions)  # 最终添加流表项
                # 配置s2的流表
                elif datapath.id == 2:
                    # 如果进入端口为eth11，将数据包转发至eth12（-s3）
                    if in_port == 11:
                        print("s2----inport:",in_port)
                        actions = [parser.OFPActionOutput(12)]
                        out_port = 12
                    # 如果进入端口为eth12，将数据包转发至eth11（-s1）
                    if in_port==12:
                        print("s2----inport:",in_port)
                        actions = [parser.OFPActionOutput(11)]
                        out_port = 11
                    match = parser.OFPMatch(in_port=in_port)  # 创建一个匹配对象，指定匹配条件为上述端口
                    self.add_flow(datapath, 1,match, actions)  # 最终添加流表项
                # 配置s3的流表
                elif datapath.id == 3:
                    print("s3----inport:",in_port)
                    actions = [parser.OFPActionOutput(1)]  # 将数据包输出端口设置为eth1（-h4）
                    match = parser.OFPMatch(in_port=in_port)  # 创建一个匹配对象，指定匹配条件为上述端口
                    self.add_flow(datapath, 1,match, actions)  # 最终添加流表项

        # 处理ARP数据包
        if arp_pkt:
            # 提取ARP包信息
            arp_src = arp_pkt.src_ip
            arp_dst = arp_pkt.dst_ip

            # 获取路径
            path = self.get_path(self.ip2host[arp_src], self.ip2host[arp_dst])
            
            # 确定当前交换机在路径中的位置并找到下一跳
            if dpid in path:
                index = path.index('s%s' % dpid)  # 获取当前交换机在路径中的位置索引
                out_port = self.graph[path[index]][path[index + 1]]['port']  # 获取下一跳交换机的端口号
                print('ARP Packet %s -> %s : port %s' % (path[index], path[index + 1], out_port))

                actions.append(parser.OFPActionOutput(out_port))  # 根据上述获得信息创建动作对象

                match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP,
                                        arp_spa=arp_src, arp_tpa=arp_dst)  # 创建一个匹配条件，匹配 ARP 包的以太网类型、源 IP 和目的 IP

                self.add_flow(datapath, 1, match, actions)  # 添加流表项

        # 处理IPv4数据包
        if ipv4_pkt:
            # 提取数据包信息
            ipv4_src = ipv4_pkt.src
            ipv4_dst = ipv4_pkt.dst

            # 获取路径
            path = self.get_path(self.ip2host[ipv4_src], self.ip2host[ipv4_dst])  # 获取从src到dst的最短路径

            # 确定当前交换机在路径中的位置并找到下一跳
            if dpid in path:
                index = path.index('s%s' % dpid)  # 获取当前交换机在路径中的位置索引
                out_port = self.graph[path[index]][path[index + 1]]['port']  # 获取下一跳交换机的端口号
                print('iPv4 Packet %s -> %s : port %s' % (path[index], path[index + 1], out_port))

                actions.append(parser.OFPActionOutput(out_port))  # 根据上述获得信息创建动作对象

                match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,
                                        ipv4_src=ipv4_src, ipv4_dst=ipv4_dst)  # 创建一个匹配条件，匹配 ARP 包的以太网类型、源 IP 和目的 IP

                self.add_flow(datapath, 1, match, actions)  # 添加流表项


        #  最终发送PacketOut信息，将数据包转发出去
        data = None
        # 若数据包不在交换机的缓冲区中，则将数据包写入data变量中
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        # 创建PacketOut信息，并发送
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

        # 清空流表
        self.empty_flow_table(datapath)
