#  implement basic controller functions


from __future__ import print_function
import element
import setting


class Controller:
    def __init__(self, topo, soft_labels=None, regions=None):
        self.topo = topo
        self.switch_num = len(topo)
        self.soft_labels = soft_labels

        self.shortest_pathes = {label: {} for label in range(self.switch_num)}
        self.get_shortest_pathes()
        
        if regions is not None:
            self.regions = regions    
            self.label2region = {}        
            for region_label in self.regions:
                region = self.regions[region_label]
                for label in region:
                    self.label2region[label] = region_label

            self.region_pathes = {label: {} for label in range(self.switch_num)}
            self.segments = {label: {} for label in range(self.switch_num)}
            self.get_region_pathes()

    def get_delay(self, path, size=1500):  # maximum Ethernet frame (1500B)
        delay = setting.LINK_RATE*size*(len(path)-1)
        for hop in path:
            if hop == setting.CTRL:
                delay += setting.CONTROLLER_DELAY
            elif self.soft_labels is not None and hop in self.soft_labels:
                delay += setting.SOFTWARE_FWD_DELAY
            else:
                delay += setting.HARDWARE_FWD_DELAY
        return delay

    def get_region_pathes(self):
        for src in range(self.switch_num):
            src_region_label = self.label2region[src]
            for dst in range(self.switch_num):
                dst_region_label = self.label2region[dst]
                if src_region_label != dst_region_label:
                    self.region_pathes[src][dst] = self.shortest_pathes[src][dst]

        for src in range(self.switch_num):
            src_region_label = self.label2region[src]
            exclude_points = [label for label in range(self.switch_num)
                              if label not in self.regions[src_region_label]]
            spathes = element.shortest_pathes(self.topo, src, exclude_points)
            for intra_dst in spathes:
                spathes[intra_dst] = sorted([(self.get_delay(sp), sp) for sp in spathes[intra_dst]])
                self.region_pathes[src][intra_dst] = [sp for (delay, sp) in spathes[intra_dst]]

        for src in range(self.switch_num):
            for dst in range(self.switch_num):
                self.segments[src][dst] = []
                for cnt in range(len(self.region_pathes[src][dst])):
                    path = self.region_pathes[src][dst][cnt]
                    segment = []
                    begin_cnt = 0
                    while (begin_cnt < len(path)):
                        region_label = self.label2region[path[begin_cnt]]
                        end_cnt = begin_cnt
                        while (end_cnt+1 < len(path) and
                               region_label == self.label2region[path[end_cnt+1]]):                            
                            end_cnt += 1
                            
                        segment.append((region_label, path[begin_cnt:end_cnt+1]))
                        begin_cnt = end_cnt+1
                    if self.label2region[src] == self.label2region[dst]:
                        assert len(segment) == 1
                    self.segments[src][dst].append(segment)
        return

    def get_shortest_pathes(self, exclude_points=None):
        for src in range(self.switch_num):
            spathes = element.shortest_pathes(self.topo, src, exclude_points)
            for dst in range(self.switch_num):
                spathes[dst] = sorted([(self.get_delay(sp), sp) for sp in spathes[dst]])
                self.shortest_pathes[src][dst] = [sp for (delay, sp) in spathes[dst]]
        return

    def region_division(self):
        for label in range(self.switch_num):
            (region, min_hop) = (None, None)
            for soft_label in self.soft_labels:
                path = self.shortest_pathes[soft_label][label][0]
                if min_hop is None or min_hop > len(path):
                    (region, min_hop) = (soft_label, len(path))
            # self.label2region[label] = region
            if region in self.regions:
                self.regions[region].append(label)
            else:
                self.regions[region] = [label]
        return

    def packet_in(self, label, pkt, mode):
        if mode == 0:  # install exact-match 5-tuple rules hop-by-hop
            return self.packet_in_default(label, pkt)
        elif mode == 1:  # install exact-match 5-tuple rules on shortest-path
            return self.packet_in_spath(label, pkt)
        else:
            raise NameError('Error. No such packet in mode. Exit.')

    def packet_in_default(self, label, pkt):  
        dst = pkt.dst
        path = self.shortest_pathes[label][dst][0]
        field = setting.FIELD_TP
        priority = 40
        match_field = pkt.tp
        action = [(setting.ACT_FWD, path[1])]
        entry = element.Entry(field, priority, match_field, action)
        inst = [(setting.INST_ADD, label, entry)]  # instructions = [(action, object, content), ...]
        return inst

    def packet_in_spath(self, label, pkt):  
        dst = pkt.dst
        path = self.shortest_pathes[label][dst][0]
        instractions = []
        field = setting.FIELD_TP
        priority = 40
        match_field = pkt.tp
        for cnt in range(len(path)-1):
            action = [(setting.ACT_FWD, path[cnt+1])]
            entry = element.Entry(field, priority, match_field, action)
            inst = (setting.INST_ADD, path[cnt], entry)
            instractions.append(inst)
        return instractions


if __name__ == '__main__':
    topo = setting.BRIDGE
    soft_labels = setting.BRIDGE_SOFT_LABELS_CORE
    c = Controller(topo, soft_labels)
    for src in c.shortest_pathes:
        for dst in c.shortest_pathes[src]:
            print('%s->%s:' % (src, dst), end='')
            print(c.shortest_pathes[src][dst], end=';')
            
    assert int(c.get_delay([0, setting.CTRL, 1])) == 4034
    assert int(c.get_delay([0, 2, 1])) == 69
