# evaluate SDLS architecture


from __future__ import print_function
import element
import setting
import network
import data
    

def sdls_ctrl_simu(net, log_prefix, check_interval=5000, upd_delay=0, policy=0, 
                   k=1.0, ctrl_delay=setting.CONTROLLER_DELAY/2):
    # print('***simulation begins***')
    
    n = net
    c = n.controller

    instractions = []
    for region_label in c.regions:
        # intra-region routing rules
        for src in c.regions[region_label]:
            for dst in c.regions[region_label]:
                if src == dst: continue
                # tag and forward by IP for src
                path = c.region_pathes[src][dst][0]
                field = setting.FIELD_DST
                priority = 1
                match_field = dst
                action = [(setting.ACT_TAG, dst), (setting.ACT_FWD, setting.LOCAL)]
                entry = element.Entry(field, priority, match_field, action)
                inst = (setting.INST_FIX, src, entry)
                instractions.append(inst)
                # forward by label
                field = setting.FIELD_LABEL
                priority = 50
                match_field = dst
                for cnt in range(1, len(path)-1):
                    action = [(setting.ACT_FWD, path[cnt+1])]
                    entry = element.Entry(field, priority, match_field, action)
                    inst = (setting.INST_FIX, path[cnt], entry)
                    instractions.append(inst)
        
        # change default action
        for src in c.regions[region_label]:
            sw = n.switches[src]
            if src == region_label: continue
            else:
                path = c.region_pathes[src][region_label][0]
                action = [
                    (setting.ACT_TAG, region_label),
                    (setting.ACT_RTAG, src),
                    (setting.ACT_FWD, path[1])
                ]
            sw.set_default_action(action)

        # software switch as a sender
        for dst in range(n.switch_num):
            if dst in c.regions[region_label]: continue
            fast_path = c.shortest_pathes[region_label][dst][0]
            (_, seg) = c.segments[region_label][dst][0][0]
            end_point = seg[-1]
            end_cnt = fast_path.index(end_point)
            next_begin_point = fast_path[end_cnt+1]
            field = setting.FIELD_DST
            priority = 1
            match_field = dst
            action = [
                (setting.ACT_TAG, end_point),
                (setting.ACT_RTAG, next_begin_point),
                (setting.ACT_FWD, setting.LOCAL)
            ]
            entry = element.Entry(field, priority, match_field, action)
            inst = (setting.INST_FIX, region_label, entry)
            instractions.append(inst)

        # inter-region routing rules
        for src in range(n.switch_num):
            for dst in range(n.switch_num):
                if c.label2region[src] == c.label2region[dst]: continue
                if dst in c.regions[region_label]: continue
                fast_path = c.shortest_pathes[src][dst][0]
                segments = c.segments[src][dst][0]                
                
                # find the segment
                for (belong_region, seg) in segments:
                    if belong_region == region_label:
                        begin_point = seg[0]
                        end_point = seg[-1]
                        end_cnt = fast_path.index(end_point)
                        next_begin_point = fast_path[end_cnt+1]
                        slow_path = c.region_pathes[region_label][end_point][0]
                        # install tagging rule
                        field = setting.FIELD_LABEL_RLABEL_DST
                        priority = 60
                        match_field = (region_label, begin_point, dst)
                        action = [
                            (setting.ACT_TAG, end_point),
                            (setting.ACT_RTAG, next_begin_point),
                            (setting.ACT_FWD, setting.LOCAL)
                        ]
                        entry = element.Entry(field, priority, match_field, action)
                        inst = (setting.INST_FIX, region_label, entry)
                        instractions.append(inst)
                        # install rule to forward packets to another region
                        field = setting.FIELD_LABEL_RLABEL
                        priority = 50
                        match_field = (end_point, next_begin_point)
                        action = [
                            (setting.ACT_TAG, None),
                            (setting.ACT_RTAG, None),
                            (setting.ACT_FWD, next_begin_point)
                        ]
                        entry = element.Entry(field, priority, match_field, action)
                        inst = (setting.INST_FIX, end_point, entry)
                        instractions.append(inst)
    n.process_ctrl_messages(instractions)

    flownum = n.traffic.flownum
    d = data.Data()
    delay = 0
    overflow_num = 0
    pktnum = 0

    inst_queue = []
    inst_point = 0

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
                raise AssertionError('Error. Packets in SDLS do not go pass controller. Exit.')
            elif next_hop == setting.LOCAL:
                dst = pkt.dst
                # intra-region routing local action
                if c.label2region[sw.label] == c.label2region[dst]:
                    intra_path = c.region_pathes[sw.label][dst][0]

                    filed = setting.FIELD_TP
                    priority = 40
                    match_field = pkt.tp
                    action = [(setting.ACT_TAG, dst), (setting.ACT_FWD, intra_path[1])]
                    entry = element.Entry(filed, priority, match_field, action)
                    instractions = [(setting.INST_ADD, sw.label, entry)]
                    of = n.process_ctrl_messages(instractions)

                    # forward
                    next_hop = intra_path[1]
                    sw = n.switches[next_hop]
                    # print('arriving switch %d' % sw.label)
                # inter-region routing local action
                else:
                    src = pkt.src
                    fast_path = c.shortest_pathes[src][dst][0]
                    segment = c.segments[src][dst][0]
                    instractions = []
                    for (belong_region, seg) in segment[:-1]:  # no need for last segment
                        begin_point = seg[0]
                        end_point = seg[-1]
                        end_cnt = fast_path.index(end_point)
                        next_begin_point = fast_path[end_cnt+1]

                        if pkt.label == end_point:
                            now_end_point = end_point
                            now_next_begin_point = next_begin_point

                        field = setting.FIELD_TP
                        priority = 40
                        match_field = pkt.tp
                        if begin_point != end_point:
                            # install forwarding entries on segment of the shortest path
                            action = [
                                (setting.ACT_TAG, end_point),
                                (setting.ACT_RTAG, next_begin_point),
                                (setting.ACT_FWD, seg[1])
                            ]
                        else:
                            action = [(setting.ACT_FWD, next_begin_point)]
                        entry = element.Entry(field, priority, match_field, action)
                        inst = (setting.INST_ADD, begin_point, entry)
                        instractions.append(inst)
                    
                    inst_queue.append((instractions, delay, pkt.tp))

                    # forward
                    if sw.label != now_end_point:
                        slow_path = c.region_pathes[sw.label][now_end_point][0]
                        next_hop = slow_path[1]
                    else:
                        next_hop = now_next_begin_point

                    sw = n.switches[next_hop]
                    # print('arriving switch %d' % sw.label)
            else:
                sw = n.switches[next_hop]
                # print('arriving switch %d' % sw.label)
            hop += 1
            assert hop < 10*len(n.topo)
        # print('pkt path = {}'.format(pkt.path))
        
        if (inst_point < len(inst_queue) and 
            inst_queue[inst_point][1]+ctrl_delay+upd_delay <= delay):
            new_inst_point = inst_point+1
            while (new_inst_point < len(inst_queue) and 
                   inst_queue[new_inst_point][1]+ctrl_delay < delay):
                new_inst_point += 1
            
            # controller update flow table in batch
            available_update = inst_queue[inst_point:new_inst_point]
            inst_point = new_inst_point
            if policy == 0:  # update all
                to_update = available_update
            elif policy == 1:  # update randomly
                from random import sample
                to_update = sample(available_update, int(k*len(available_update)))
            elif policy == 2:  # select elephant flow
                flow_cnt = {}
                for (_, _, tp) in available_update:
                    if tp in flow_cnt:
                        flow_cnt[tp] += 1
                    else:
                        flow_cnt[tp] = 1
                select_tp = sorted(flow_cnt, key=lambda e: flow_cnt[e], reverse=True)[:int(k*len(flow_cnt))]
                to_update = []
                for update in available_update:
                    if update[2] in select_tp:
                        to_update.append(update)
            else:
                raise NameError('Error. No such policy. Exit.')
                exit(1)

            for (instractions, _, _) in to_update:
                of += n.process_ctrl_messages(instractions)

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
    
    sdls_ctrl_simu(n, log_prefix='./data/sdls_ctrl_ge50_noftc')
    return    


def eva_ge50_ftc():
    topo = setting.GE50
    traffic_logfile = setting.GE50_TRAFFIC_LOGFILE
    soft_labels = setting.GE50_SOFT_LABELS[3]
    regions = setting.GE50_REGIONS[3]

    n = network.Network(topo, soft_labels, regions)
    n.generate_log_traffic(traffic_logfile)
    
    sdls_ctrl_simu(n, log_prefix='./data/sdls_ctrl_ge50_ftc')
    return


def eva_brain_noftc():
    topo = setting.BRAIN
    traffic_logfile = setting.BRAIN_TRAFFIC_LOGFILE
    soft_labels = setting.BRAIN_SOFT_LABELS_CORE
    regions = setting.BRAIN_REGIONS
    
    setting.FLOW_TABLE_SIZE = setting.UNLIMITED_FLOW_TABLE  # no FTC

    n = network.Network(topo, soft_labels, regions)
    n.generate_log_traffic(traffic_logfile)
    
    sdls_ctrl_simu(n, log_prefix='./data/sdls_ctrl_brain_noftc')
    return    


def eva_brain_ftc():
    topo = setting.BRAIN
    traffic_logfile = setting.BRAIN_TRAFFIC_LOGFILE
    soft_labels = setting.BRAIN_SOFT_LABELS_CORE
    regions = setting.BRAIN_REGIONS

    n = network.Network(topo, soft_labels, regions)
    n.generate_log_traffic(traffic_logfile)
    
    sdls_ctrl_simu(n, log_prefix='./data/sdls_ctrl_brain_ftc')
    return


def eva_burst_noftc():
    topo = setting.GE50
    traffic_logfile = setting.GE50_BURST_TRAFFIC_LOGFILE
    soft_labels = setting.GE50_SOFT_LABELS[3]
    regions = setting.GE50_REGIONS[3]

    setting.FLOW_TABLE_SIZE = setting.UNLIMITED_FLOW_TABLE  # no FTC

    n = network.Network(topo, soft_labels, regions)
    n.generate_log_traffic(traffic_logfile)
    
    sdls_ctrl_simu(n, log_prefix='./data/sdls_ctrl_burst_noftc')
    return    


def eva_burst_ftc():
    topo = setting.GE50
    traffic_logfile = setting.GE50_BURST_TRAFFIC_LOGFILE
    soft_labels = setting.GE50_SOFT_LABELS[3]
    regions = setting.GE50_REGIONS[3]

    n = network.Network(topo, soft_labels, regions)
    n.generate_log_traffic(traffic_logfile)
    
    sdls_ctrl_simu(n, log_prefix='./data/sdls_ctrl_burst_ftc')
    return    


def eva_tail_noftc():
    topo = setting.GE50
    traffic_logfile = setting.GE50_TAIL_TRAFFIC_LOGFILE
    soft_labels = setting.GE50_SOFT_LABELS[3]
    regions = setting.GE50_REGIONS[3]

    setting.FLOW_TABLE_SIZE = setting.UNLIMITED_FLOW_TABLE  # no FTC

    n = network.Network(topo, soft_labels, regions)
    n.generate_log_traffic(traffic_logfile)
    
    sdls_ctrl_simu(n, log_prefix='./data/sdls_ctrl_tail_noftc', check_interval=100)
    return


def eva_tail_ftc():
    topo = setting.GE50
    traffic_logfile = setting.GE50_TAIL_TRAFFIC_LOGFILE
    soft_labels = setting.GE50_SOFT_LABELS[3]
    regions = setting.GE50_REGIONS[3]

    n = network.Network(topo, soft_labels, regions)
    n.generate_log_traffic(traffic_logfile)
    
    sdls_ctrl_simu(n, log_prefix='./data/sdls_ctrl_tail_ftc', check_interval=100)
    return


def test_eva():
    import traffic

    print('testing')
    topo = setting.BRIDGE
    soft_labels = setting.BRIDGE_SOFT_LABELS_CORE
    regions = setting.BRIDGE_REGIONS

    n = network.Network(topo, soft_labels, regions)    
    n.generate_sample_traffic(dup=2)
    # n.generate_log_traffic(setting.BRIDGE_TRAFFIC_LOGFILE)

    # setting.FLOW_TABLE_SIZE = [60, 60]

    d = sdls_ctrl_simu(n, log_prefix='./data/sdls_ctrl_test', check_interval=1, ctrl_delay=0)
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