# evaluate normal OpenFlow architecture


from __future__ import print_function
import element
import setting
import network
import data
    

def openflow_simu(net, mode, log_prefix, check_interval=5000):
    # print('***simulation begins***')

    n = net
    c = n.controller

    flownum = n.traffic.flownum
    d = data.Data()
    delay = 0
    overflow_num = 0
    pktnum = 0
    
    for pkt in n.traffic.pkts:
        # print('processing packet');pkt.print_pkt()
        sw = n.switches[pkt.src]
        # print('arriving switch %d' % sw.label)
        hop = 0
        of = 0
        while True:
            if pkt.dst == sw.label:  # abandon using receving entry
                pkt.path.append(sw.label)
                break
            [pkt, next_hop] = sw.recv_pkt(pkt)
            # print('\tforwarding to %s' % str(next_hop))
            if next_hop == setting.CTRL:
                instractions = c.packet_in(sw.label, pkt, mode)
                of = n.process_ctrl_messages(instractions)
            else:
                sw = n.switches[next_hop]
                # print('arriving switch %d' % sw.label)
            hop += 1
            assert hop < 10*len(n.topo)
        # print('pkt path = {}'.format(pkt.path))
        
        fnum = flownum[pktnum]  # why minus 1?
        pktnum += 1
        overflow_num += of
        pkttime = c.get_delay(pkt.path, pkt.size)
        delay += pkttime

        flowsize = n.traffic.flowsize[pkt.tp]
        d.record_fct(pkt.tp, pkttime, flowsize)
        
        if fnum%check_interval == 0:
            if fnum not in d.delay['flownum']:
                instractions = [(setting.INST_QUERY, setting.INST_OBJ_ALL, None)]
                totentry = n.process_ctrl_messages(instractions)
                maxentry = 0
                for label in range(n.switch_num):
                    instractions = [(setting.INST_QUERY, setting.INST_OBJ_TABLE, label)]
                    maxentry = max(maxentry, n.process_ctrl_messages(instractions))

                d.record(fnum, delay, totentry, maxentry, overflow_num)
                d.print_checkpoint(fnum, log_prefix+'_checkpoint.txt')

    d.print_data(log_prefix)

    return


def eva_ge50_noftc():
    topo = setting.GE50
    traffic_logfile = setting.GE50_TRAFFIC_LOGFILE

    setting.FLOW_TABLE_SIZE = setting.UNLIMITED_FLOW_TABLE  # no FTC

    n = network.Network(topo)  # no software switches
    n.generate_log_traffic(traffic_logfile)
    
    openflow_simu(n, mode=1, log_prefix='./data/openflow_ge50_noftc')
    return    

def eva_ge50_ftc():
    topo = setting.GE50
    traffic_logfile = setting.GE50_TRAFFIC_LOGFILE

    n = network.Network(topo)  # no software switches
    n.generate_log_traffic(traffic_logfile)
    
    openflow_simu(n, mode=1, log_prefix='./data/openflow_ge50_ftc')
    return


def eva_brain_noftc():
    topo = setting.BRAIN
    traffic_logfile = setting.BRAIN_TRAFFIC_LOGFILE

    setting.FLOW_TABLE_SIZE = setting.UNLIMITED_FLOW_TABLE  # no FTC

    n = network.Network(topo)  # no software switches
    n.generate_log_traffic(traffic_logfile)

    openflow_simu(n, mode=1, log_prefix='./data/openflow_brain_noftc')
    return


def eva_brain_ftc():
    topo = setting.BRAIN
    traffic_logfile = setting.BRAIN_TRAFFIC_LOGFILE

    n = network.Network(topo)  # no software switches
    n.generate_log_traffic(traffic_logfile)

    openflow_simu(n, mode=1, log_prefix='./data/openflow_brain_ftc')
    return


def eva_burst_noftc():
    topo = setting.GE50
    traffic_logfile = setting.GE50_BURST_TRAFFIC_LOGFILE

    setting.FLOW_TABLE_SIZE = setting.UNLIMITED_FLOW_TABLE  # no FTC

    n = network.Network(topo)  # no software switches
    n.generate_log_traffic(traffic_logfile)
    
    openflow_simu(n, mode=1, log_prefix='./data/openflow_burst_noftc')
    
    return


def eva_burst_ftc():
    topo = setting.GE50
    traffic_logfile = setting.GE50_BURST_TRAFFIC_LOGFILE

    n = network.Network(topo)  # no software switches
    n.generate_log_traffic(traffic_logfile)
    
    openflow_simu(n, mode=1, log_prefix='./data/openflow_burst_ftc')
    
    return


def eva_tail_noftc():
    topo = setting.GE50
    traffic_logfile = setting.GE50_TAIL_TRAFFIC_LOGFILE

    setting.FLOW_TABLE_SIZE = setting.UNLIMITED_FLOW_TABLE  # no FTC

    n = network.Network(topo)  # no software switches
    n.generate_log_traffic(traffic_logfile)
    
    openflow_simu(n, mode=1, log_prefix='./data/openflow_tail_noftc', check_interval=100)
    
    return


def eva_tail_ftc():
    topo = setting.GE50
    traffic_logfile = setting.GE50_TAIL_TRAFFIC_LOGFILE

    n = network.Network(topo)  # no software switches
    n.generate_log_traffic(traffic_logfile)
    
    openflow_simu(n, mode=1, log_prefix='./data/openflow_tail_ftc', check_interval=100)
    
    return


def test_eva():
    print('testing')
    topo = setting.BRIDGE

    n = network.Network(topo)  # no software switches
    n.generate_sample_traffic()
    # n.generate_log_traffic(setting.BRIDGE_TRAFFIC_LOGFILE)

    # setting.FLOW_TABLE_SIZE = [60, 60]

    d = openflow_simu(n, mode=1, log_prefix='./data/openflow_test', check_interval=1)
    return
    

if __name__ == '__main__':
    from sys import argv
    switch = 0
    if len(argv) == 2:
        switch = int(argv[1])

    if switch == 1:
        eva_ge50_noftc()
    elif switch == 2:
        eva_ge50_ftc()
    elif switch == 3:
        eva_brain_noftc()
    elif switch == 4:
        eva_brain_ftc()
    elif switch == 5:
        eva_burst_noftc()
    elif switch == 6:
        eva_tail_noftc()
    elif switch == 7:
        eva_burst_ftc()
    elif switch == 8:
        eva_tail_ftc()
    else:
        test_eva()
