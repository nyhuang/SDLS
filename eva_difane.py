# evaluate DIFANE architecture


from __future__ import print_function
import element
import setting
import network
import data
    

def difane_simu(net, log_prefix, check_interval=5000):
    # print('***simulation begins***')
    
    n = net
    c = n.controller

    instractions = []
    for region_label in c.regions:
        for dst in c.regions[region_label]:
            # install relay rule to forward packets from auth. switch to egress
            path = c.shortest_pathes[region_label][dst][0]
            field = setting.FIELD_LABEL
            priority = 50
            match_field = dst
            for cnt in range(1, len(path)-1):
                action = [(setting.ACT_FWD, path[cnt+1])]
                entry = element.Entry(field, priority, match_field, action)
                inst = (setting.INST_FIX, path[cnt], entry)
                instractions.append(inst)
                
            for src in range(n.switch_num):
                if src == dst: continue
                # install auth. rule to trigger local action
                field = setting.FIELD_LABEL_SRC_DST
                priority = 50
                match_field = (region_label, src, dst)
                action = [(setting.ACT_TAG, dst), (setting.ACT_FWD, setting.LOCAL)]
                entry = element.Entry(field, priority, match_field, action)
                inst = (setting.INST_FIX, region_label, entry)
                instractions.append(inst)
                
                path = c.shortest_pathes[src][region_label][0]
                if len(path) > 1:  # src != region_label
                    # install part. rule to forward unknown packets to
                    # corresponding auth. swich
                    field = setting.FIELD_DST
                    priority = 1
                    match_field = dst
                    action = [(setting.ACT_TAG, region_label), (setting.ACT_FWD, path[1])]
                    entry = element.Entry(field, priority, match_field, action)
                    inst = (setting.INST_FIX, src, entry)
                    instractions.append(inst)

                    # install relay rule to forward packets to auth. switch
                    field = setting.FIELD_LABEL
                    priority = 50
                    match_field = region_label
                    action = [(setting.ACT_FWD, path[1])]
                    entry = element.Entry(field, priority, match_field, action)
                    inst = (setting.INST_FIX, src, entry)
                    instractions.append(inst)
                else:
                    # src == region_label: forward to local
                    field = setting.FIELD_DST
                    priority = 1
                    match_field = dst
                    action = [(setting.ACT_FWD, setting.LOCAL)]
                    entry = element.Entry(field, priority, match_field, action)
                    inst = (setting.INST_FIX, src, entry)
                    instractions.append(inst)

    n.process_ctrl_messages(instractions)
    
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
                raise AssertionError('Error. Packets in DIFANE do not go pass controller. Exit.')
            elif next_hop == setting.LOCAL:
                # perform local actions
                # install forwarding entries on shortest path
                instractions = []
                src = pkt.src
                dst = pkt.dst
                fast_path = c.shortest_pathes[src][dst][0]
                field = setting.FIELD_TP
                priority = 40
                match_field = pkt.tp
                for cnt in range(len(fast_path)-1):
                    action = [(setting.ACT_FWD, fast_path[cnt+1])]
                    entry = element.Entry(field, priority, match_field, action)
                    inst = (setting.INST_ADD, fast_path[cnt], entry)
                    instractions.append(inst)
                of = n.process_ctrl_messages(instractions)

                # forward
                slow_path = c.shortest_pathes[sw.label][dst][0]
                next_hop = slow_path[1]
                sw = n.switches[next_hop]
                # print('arriving switch %d' % sw.label)
            else:
                sw = n.switches[next_hop]
                # print('arriving switch %d' % sw.label)
            hop += 1
            assert hop < 10*len(n.topo)
        # print('pkt path = {}'.format(pkt.path))

        fnum = flownum[pktnum]
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
    soft_labels = setting.GE50_SOFT_LABELS[3]
    regions = setting.GE50_REGIONS[3]
    
    setting.FLOW_TABLE_SIZE = setting.UNLIMITED_FLOW_TABLE  # no FTC

    n = network.Network(topo, soft_labels, regions)
    n.generate_log_traffic(traffic_logfile)
    
    difane_simu(n, log_prefix='./data/difane_ge50_noftc')
    return


def eva_ge50_ftc():
    topo = setting.GE50
    traffic_logfile = setting.GE50_TRAFFIC_LOGFILE
    soft_labels = setting.GE50_SOFT_LABELS[3]
    regions = setting.GE50_REGIONS[3]

    n = network.Network(topo, soft_labels, regions)
    n.generate_log_traffic(traffic_logfile)
    
    difane_simu(n, log_prefix='./data/difane_ge50_ftc')
    return


def eva_brain_noftc():
    topo = setting.BRAIN
    traffic_logfile = setting.BRAIN_TRAFFIC_LOGFILE
    soft_labels = setting.BRAIN_SOFT_LABELS_CORE
    regions = setting.BRAIN_REGIONS
    
    setting.FLOW_TABLE_SIZE = setting.UNLIMITED_FLOW_TABLE  # no FTC

    n = network.Network(topo, soft_labels, regions)
    n.generate_log_traffic(traffic_logfile)
    
    difane_simu(n, log_prefix='./data/difane_brain_noftc')
    return    


def eva_brain_ftc():
    topo = setting.BRAIN
    traffic_logfile = setting.BRAIN_TRAFFIC_LOGFILE
    soft_labels = setting.BRAIN_SOFT_LABELS_CORE
    regions = setting.BRAIN_REGIONS

    n = network.Network(topo, soft_labels, regions)
    n.generate_log_traffic(traffic_logfile)
    
    difane_simu(n, log_prefix='./data/difane_brain_ftc')
    return


def eva_burst_noftc():
    topo = setting.GE50
    traffic_logfile = setting.GE50_BURST_TRAFFIC_LOGFILE
    soft_labels = setting.GE50_SOFT_LABELS[3]
    regions = setting.GE50_REGIONS[3]
    
    setting.FLOW_TABLE_SIZE = setting.UNLIMITED_FLOW_TABLE  # no FTC

    n = network.Network(topo, soft_labels, regions)
    n.generate_log_traffic(traffic_logfile)
    
    difane_simu(n, log_prefix='./data/difane_burst_noftc')
    return


def eva_burst_ftc():
    topo = setting.GE50
    traffic_logfile = setting.GE50_BURST_TRAFFIC_LOGFILE
    soft_labels = setting.GE50_SOFT_LABELS[3]
    regions = setting.GE50_REGIONS[3]
    
    n = network.Network(topo, soft_labels, regions)
    n.generate_log_traffic(traffic_logfile)
    
    difane_simu(n, log_prefix='./data/difane_burst_ftc')
    return


def eva_tail_noftc():
    topo = setting.GE50
    traffic_logfile = setting.GE50_TAIL_TRAFFIC_LOGFILE
    soft_labels = setting.GE50_SOFT_LABELS[3]
    regions = setting.GE50_REGIONS[3]
    
    setting.FLOW_TABLE_SIZE = setting.UNLIMITED_FLOW_TABLE  # no FTC

    n = network.Network(topo, soft_labels, regions)
    n.generate_log_traffic(traffic_logfile)
    
    difane_simu(n, log_prefix='./data/difane_tail_noftc', check_interval=100)
    return


def eva_tail_ftc():
    topo = setting.GE50
    traffic_logfile = setting.GE50_TAIL_TRAFFIC_LOGFILE
    soft_labels = setting.GE50_SOFT_LABELS[3]
    regions = setting.GE50_REGIONS[3]
    
    n = network.Network(topo, soft_labels, regions)
    n.generate_log_traffic(traffic_logfile)
    
    difane_simu(n, log_prefix='./data/difane_tail_ftc', check_interval=100)
    return


def test_eva():
    print('testing')
    topo = setting.BRIDGE
    soft_labels = setting.BRIDGE_SOFT_LABELS_CORE
    regions = setting.BRIDGE_REGIONS

    n = network.Network(topo, soft_labels, regions)
    n.generate_sample_traffic()
    # n.generate_log_traffic(setting.BRIDGE_TRAFFIC_LOGFILE)

    # setting.FLOW_TABLE_SIZE = [60, 60]

    difane_simu(n, log_prefix='./data/difane_test', check_interval=1)
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
