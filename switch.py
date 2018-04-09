#  implement basic hw switch functions


from __future__ import print_function
import element
import traffic
import setting


class Switch:
    def __init__(self, label, sw_type=setting.TYPE_HARDWARE):
        self.label = label
        self.fix_table = []
        self.flow_table = []

        self.fast_table = {}
        
        self.default_action = [(setting.ACT_FWD, setting.CTRL)]
        self.sw_type = sw_type

    def set_sw_type(self, sw_type):
        self.sw_type = sw_type
        return 0

    def set_default_action(self, default_action):
        self.default_action = default_action
        return 0

    def get_size(self):
        return len(self.flow_table)+len(self.fix_table)

    def update(self):
        table_size = self.get_size()
        max_size = setting.FLOW_TABLE_SIZE[self.sw_type]
        # print('fix table size = {}'.format(len(self.fix_table)))
        assert len(self.fix_table) < max_size
        if table_size > max_size:
            # remove from fast table
            to_remove = self.flow_table[:(table_size-max_size+1)]
            for entry in to_remove:
                self.fast_table[entry.field][entry.match_field] = None
            self.flow_table = self.flow_table[(table_size-max_size+1):]
            return 1  # overflow
        return 0

    def add_entry(self, entry, fix=False):
        
        def add_fast_entry(entry):
            if entry.field in self.fast_table:
                self.fast_table[entry.field][entry.match_field] = entry
            else:
                self.fast_table[entry.field] = {entry.match_field: entry}
            return

        if entry.field in self.fast_table:
            if entry.match_field in self.fast_table[entry.field]:
                old_entry = self.fast_table[entry.field][entry.match_field]
                # exists old entry
                if old_entry is not None:
                    # replace with new entry
                    if entry.priority > old_entry.priority:
                        self.fast_table[entry.field][entry.match_field] = entry
                    return 0

        if fix:
            self.fix_table.append(entry)
            add_fast_entry(entry)
            # print('fix entry at s%d:' % self.label, end=''); entry.print_entry()
            return 0
        else:
            isof = self.update()
            self.flow_table.append(entry)
            add_fast_entry(entry)
            # print('add entry at s%d:' % self.label, end=''); entry.print_entry()
            return isof

    def get_match_entry(self, pkt):
        match_entry = element.Entry(None, -1, None, None)

        def comp_entry(new_entry, old_entry):
            if new_entry.priority > old_entry.priority:
                return new_entry
            elif new_entry.priority == old_entry.priority:  # TODO: ECMP
                return old_entry
            else:
                return old_entry

        # fast match (exact matching)
        # sequential matching against label(50) -> tuple(40) -> dstip(32) -> others
        if setting.FIELD_LABEL_SRC_DST in self.fast_table:
            if (pkt.label, pkt.src, pkt.dst) in self.fast_table[setting.FIELD_LABEL_SRC_DST]:
                entry = self.fast_table[setting.FIELD_LABEL_SRC_DST][(pkt.label, pkt.src, pkt.dst)]
                if entry is not None:
                    match_entry = comp_entry(entry, match_entry)

        if setting.FIELD_LABEL_RLABEL_DST in self.fast_table:
            if (pkt.label, pkt.rlabel, pkt.dst) in self.fast_table[setting.FIELD_LABEL_RLABEL_DST]:
                entry = self.fast_table[setting.FIELD_LABEL_RLABEL_DST][(pkt.label, pkt.rlabel, pkt.dst)]
                if entry is not None:
                    match_entry = comp_entry(entry, match_entry)

        if setting.FIELD_LABEL in self.fast_table:
            if pkt.label in self.fast_table[setting.FIELD_LABEL]:
                entry = self.fast_table[setting.FIELD_LABEL][pkt.label]
                if entry is not None:
                    match_entry = comp_entry(entry, match_entry)

        if setting.FIELD_LABEL_RLABEL in self.fast_table:
            if (pkt.label, pkt.rlabel) in self.fast_table[setting.FIELD_LABEL_RLABEL]:
                entry = self.fast_table[setting.FIELD_LABEL_RLABEL][(pkt.label, pkt.rlabel)]
                if entry is not None:
                    match_entry = comp_entry(entry, match_entry)

        if setting.FIELD_TP in self.fast_table:
            if pkt.tp in self.fast_table[setting.FIELD_TP]:
                entry = self.fast_table[setting.FIELD_TP][pkt.tp]
                if entry is not None:
                    match_entry = comp_entry(entry, match_entry)

        if setting.FIELD_DSTIP in self.fast_table:
            if pkt.dstip in self.fast_table[setting.FIELD_DSTIP]:
                entry = self.fast_table[setting.FIELD_DSTIP][pkt.dstip]
                if entry is not None:
                    match_entry = comp_entry(entry, match_entry)

        if setting.FIELD_DST in self.fast_table:
            if pkt.dst in self.fast_table[setting.FIELD_DST]:
                entry = self.fast_table[setting.FIELD_DST][pkt.dst]
                if entry is not None:
                    match_entry = comp_entry(entry, match_entry)

        # TODO: slow match (wildcard matching)

        return match_entry

    def get_match_action(self, pkt):
        match_entry = self.get_match_entry(pkt)
        if match_entry.action is None:
            return self.default_action
        else:
            # match_entry.print_entry()
            match_entry.counter += 1
            return match_entry.action

    def recv_pkt(self, pkt, flags=None):
        action = self.get_match_action(pkt)  # action = [(type, value), ...]

        for act in action:
            act_type = act[0]
            if act_type == setting.ACT_TAG:
                pkt.label = act[1]
            elif act_type == setting.ACT_RTAG:
                pkt.rlabel = act[1]
            elif act_type == setting.ACT_FWD:
                next_hop = act[1]
            else:
                raise NameError('Error. No such act type. Exit.')

        pkt.path.append(self.label)

        if next_hop == setting.CTRL:
            pkt.path.append(setting.CTRL)
        
        return [pkt, next_hop]

    def print_table(self, filename=None):
        for entry in self.flow_table:
            entry.print_entry(filename)
        return 0


if __name__ == '__main__':
    label = 1
    sw = Switch(label)
    entry = element.Entry(setting.FIELD_DSTIP, 32, '1.2.3.4', 
                          [(setting.ACT_FWD, 2)])
    sw.add_entry(entry)
    pkt = traffic.Packet(('0.0.3.0', '1.2.3.4'))
    [pkt, next_hop] = sw.recv_pkt(pkt)
    assert next_hop == 2

    entry = element.Entry(setting.FIELD_DSTIP, 40, '1.2.3.4', 
                          [(setting.ACT_TAG, 10), (setting.ACT_FWD, 10)])
    sw.add_entry(entry)
    entry = element.Entry(setting.FIELD_DSTIP, 10, '1.2.3.4', 
                          [(setting.ACT_TAG, 10), (setting.ACT_FWD, 10)])
    sw.add_entry(entry)
    [pkt, next_hop] = sw.recv_pkt(pkt)
    assert next_hop == 10
    assert pkt.label == 10
    assert sw.get_size() == 1

    setting.FLOW_TABLE_SIZE[0] = 1
    sw.update()
    assert sw.get_size() == 1
    
    entry = element.Entry(
        setting.FIELD_LABEL_SRC_DST,
        50,
        (10, 1, 2),
        [(setting.ACT_FWD, setting.LOCAL)]
    )
    sw.add_entry(entry)
    pkt.dst = 2
    [pkt, next_hop] = sw.recv_pkt(pkt)
    assert next_hop == 10
    pkt.src = 1
    [pkt, next_hop] = sw.recv_pkt(pkt)
    assert next_hop == setting.LOCAL
    