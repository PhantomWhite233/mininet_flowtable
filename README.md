# mininet_flowtable

拓扑：remote_134.py

控制器:ryu.py

发送数据包：h1_send_data1.py h1_send_data2.py

接收数据包：receive.py

先运行拓扑
sudo mn --custom remote_134.py --topo=mytopo --controller=remote,ip=127.0.0.1,port=6633

再运行ryu.py
ryu-manager ryu.py

用xterm指令打开h1,h2,h4的终端界面，方便分别操作

在h2和h4上分别运行receive.py（我这里有警告，但是似乎并不影响功能，所以没管）

在h1上分别发送data1,data2。发送data1时h2收到，发送data2时h4收到，同样有警告，同样没管

遇到的坑：
1.	添加过流表后必须删除才能对这个端口添加新的流表
2.	执行流表删除功能代码的位置很重要
