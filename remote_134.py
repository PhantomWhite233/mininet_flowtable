from mininet.topo import Topo

class MyTopo(Topo):

    def __init__(self):
        super(MyTopo,self).__init__()

        # add host
        Host1 = self.addHost('h1',ip='10.0.0.1', mac='00:00:00:00:00:01')
        Host2 = self.addHost('h2',ip='10.0.0.2', mac='00:00:00:00:00:02')
        Host3 = self.addHost('h3',ip='10.0.0.3', mac='00:00:00:00:00:03')
        Host4 = self.addHost('h4',ip='10.0.0.4', mac='00:00:00:00:00:04')

        switch1 = self.addSwitch('s1')
        switch2 = self.addSwitch('s2')
        switch3 = self.addSwitch('s3')

        self.addLink(Host1,switch1,port1=1,port2=1)
        self.addLink(Host2,switch1,port1=1,port2=2)
        self.addLink(Host3,switch2,port1=1,port2=1)
        self.addLink(Host4,switch3,port1=1,port2=1)

        self.addLink(switch1,switch2,port1=10,port2=11)
        self.addLink(switch2,switch3,port1=12,port2=13)



        #self.addLink(switch1,switch2)

topos = {"mytopo":(lambda:MyTopo())}