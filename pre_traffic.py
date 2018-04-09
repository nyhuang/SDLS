#  pre-serialize pcap file


import traffic
import element
import setting
import network


def pre_pcap(pcap_filelist, pkl_file, max_flownum=None, json_file=None):
    print('serialize {} into {}'.format(pcap_filelist, pkl_file))
    t = traffic.Traffic()
    for pcap_file in pcap_filelist:
        print('processing {}...'.format(pcap_file))
        pkts = traffic.pcap2pkts(pcap_file)
        t.add_pkts(pkts)
        flownum = t.flownum[-1]
        print('flow number: {}'.format(flownum))
        if max_flownum is not None and flownum > max_flownum:
            break
    t.serialize(pkl_file)
    print('target flow number: {}; real flow number: {}'.format(max_flownum, t.flownum[-1]))
    print('total number of packets: {}'.format(len(t.pkts)))
    if json_file is not None:
        t.print_traffic_data(json_file)
    return


def pre_brain(pkl_file):
    print('brain: transform {} into {}'.format(pkl_file, setting.BRAIN_TRAFFIC_LOGFILE))

    topo = setting.BRAIN
    sw_list = setting.BRAIN_SOFT_LABELS_EDGE  # senders

    n = network.Network(topo)
    n.generate_real_traffic(pkl_file, sw_list)
    n.traffic.serialize(setting.BRAIN_TRAFFIC_LOGFILE)
    n.traffic.print_traffic_data(setting.BRAIN_TRAFFIC_DATA)

    print('flow number: {}'.format(n.traffic.flownum[-1]))
    return

    
def pre_ge(pkl_file):
    print('ge50: transform {} into {}'.format(pkl_file, setting.GE50_TRAFFIC_LOGFILE))

    topo = setting.GE50
    sw_list = setting.GE50_SOFT_LABELS['edge']

    n = network.Network(topo)
    n.generate_real_traffic(pkl_file, sw_list)
    n.traffic.serialize(setting.GE50_TRAFFIC_LOGFILE)
    n.traffic.print_traffic_data(setting.GE50_TRAFFIC_DATA)

    print('flow number: {}'.format(n.traffic.flownum[-1]))
    return


def pre_bridge(pkl_file):
    print('bridge: transform {} into {}'.format(pkl_file, setting.BRIDGE_TRAFFIC_LOGFILE))

    topo = setting.BRIDGE
    sw_list = setting.BRIDGE_SOFT_LABELS_EDGE

    n = network.Network(topo)
    n.generate_real_traffic(pkl_file, sw_list)
    n.traffic.serialize(setting.BRIDGE_TRAFFIC_LOGFILE)
    n.traffic.print_traffic_data(setting.BRIDGE_TRAFFIC_DATA)

    print('flow number: {}'.format(n.traffic.flownum[-1]))
    return


def pre_syn(flownum, burst_max, pktsize, exp, log_file, json_file):
    print('syn: generating synthetic traffic (flownum: {}, maximum flow: {}B, exp: {})'
          .format(flownum, burst_max * 1500, exp))

    topo = setting.GE50
    n = network.Network(topo)

    n.generate_random_traffic(setting.GE50_TRAFFIC_MAT, flownum, burst_max, exp, pktsize)
    n.traffic.serialize(log_file)
    n.traffic.print_traffic_data(json_file)

    print('flow number: {}; packet number: {}'.format(n.traffic.flownum[-1], len(n.traffic.pkts)))
    return


def test_pre_traffic():
    pcap_filelist = ['sample.pcap']
    pkl_file = 'sample.pkl'

    pre_pcap(pcap_filelist, pkl_file, json_file='sample.json')

    pre_bridge(pkl_file)

    return


def pre_burst():
    max_flowsize = 10240  # 100KB
    pktsize = 60
    burst_max = max_flowsize / 1500
    flownum = 1005000
    exp = 5

    pre_syn(flownum, burst_max, pktsize, exp, 
            setting.GE50_BURST_TRAFFIC_LOGFILE,
            setting.GE50_BURST_TRAFFIC_DATA)
    return 
 

def pre_tail():
    max_flowsize = 10*1024*1024  # 10MB
    pktsize = 1500
    flownum = 10
    exp = 0.5
    burst_max = max_flowsize / pktsize

    pre_syn(flownum, burst_max, pktsize, exp, 
            setting.GE50_TAIL_TRAFFIC_LOGFILE,
            setting.GE50_TAIL_TRAFFIC_DATA)

    return 
    

def pre_slice_pcap():
    for i in range(25):
        start = 1+i*1000000
        end = (i+1)*1000000
        print('editcap -r tf real{}-{}.pcap {}-{} -F pcap &'
              .format(i, i+1, start, end))
    return


def pre_real_pcap():
    # [0, ~15000000] pkts
    pcap_filelist = ['real{}-{}.pcap'.format(i, i+1) for i in range(0, 25)]
    pkl_file = 'real.pkl'
    json_file = 'real.json'
    max_flownum = 1001000

    pre_pcap(pcap_filelist, pkl_file, max_flownum, json_file)
    return


def pre_real_pkl():
    pkl_file = 'real.pkl'
    pre_ge(pkl_file)
    pre_brain(pkl_file)
    return


if __name__ == '__main__':
    test_pre_traffic()
