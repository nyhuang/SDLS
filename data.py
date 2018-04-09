from __future__ import print_function
from time import time
import json


class Data:
    def __init__(self):
        self.start = time()

        self.delay = {'flownum': [], 'delay': []}
        self.totentry = {'flownum': [], 'totentry': []}
        self.maxentry = {'flownum': [], 'maxentry': []}
        self.overflow_num = {'flownum': [], 'overflow_num': []}
        self.fct = {}

        self.threshold = 102400  # 100KB
        self.burst_fct = {}
        self.tail_fct = {}

        # self.ctrlmsg_num = {}
        # self.stretches = {}        

    def record(self, flownum, delay, totentry, maxentry, overflow_num):
        self.delay['flownum'].append(flownum)
        self.delay['delay'].append(delay)
        self.totentry['flownum'].append(flownum)
        self.totentry['totentry'].append(totentry)
        self.maxentry['flownum'].append(flownum)
        self.maxentry['maxentry'].append(maxentry)
        self.overflow_num['flownum'].append(flownum)
        self.overflow_num['overflow_num'].append(overflow_num)
        return

    def record_fct(self, tp, pkttime, flowsize):
        # if tp in self.fct:
        #     self.fct[tp] += pkttime
        # else:
        #     self.fct[tp] = pkttime
        if flowsize > self.threshold:
            if tp in self.tail_fct:
                self.tail_fct[tp] += pkttime
            else:
                self.tail_fct[tp] = pkttime
        else:
            if tp in self.burst_fct:
                self.burst_fct[tp] += pkttime
            else:
                self.burst_fct[tp] = pkttime
        return

    def print_checkpoint(self, fnum, filename=None):
        with open(filename, 'a') as f:
            print('{} {}'.format(time()-self.start, fnum), file=f)
        return


    def get_fct_cdf(self, fct):
        fct_cnt = {}
        tot = len(fct)
        for tp in fct:
            delay = fct[tp]
            if delay in fct_cnt:
                fct_cnt[delay] += 1
            else:
                fct_cnt[delay] = 1
        cp = 0.0
        cdf_x = []
        cdf_y = []
        for t in sorted(fct_cnt):
            p = 1.0 * fct_cnt[t] / tot
            cp += p
            cdf_x.append(t)
            cdf_y.append(cp)

        cdf = {'x': cdf_x, 'y': cdf_y}
        return cdf


    def print_data(self, fileprefix):
        with open(fileprefix+'_delay.json', 'w') as f:
            print(json.dumps(self.delay), file=f)
        with open(fileprefix+'_totentry.json', 'w') as f:
            print(json.dumps(self.totentry), file=f)
        with open(fileprefix+'_maxentry.json', 'w') as f:
            print(json.dumps(self.maxentry), file=f)
        with open(fileprefix+'_overflow_num.json', 'w') as f:
            print(json.dumps(self.overflow_num), file=f)
        # with open(fileprefix+'_fct.json', 'w') as f:
        #     fct_str = {}
        #     for tp in self.fct:
        #         fct_str[str(tp)] = self.fct[tp]
        #     print(json.dumps(fct_str), file=f)
        with open(fileprefix+'_burst_fct.json', 'w') as f:
            fct_str = {}
            for tp in self.burst_fct:
                fct_str[str(tp)] = self.burst_fct[tp]
            print(json.dumps(fct_str), file=f)
        with open(fileprefix+'_tail_fct.json', 'w') as f:
            fct_str = {}
            for tp in self.tail_fct:
                fct_str[str(tp)] = self.tail_fct[tp]
            print(json.dumps(fct_str), file=f)
        
        burst_fct_cdf = self.get_fct_cdf(self.burst_fct)
        with open(fileprefix+'_burst_fct_cdf.json', 'w') as f:
            print(json.dumps(burst_fct_cdf), file=f)
        tail_fct_cdf = self.get_fct_cdf(self.tail_fct)
        with open(fileprefix+'_tail_fct_cdf.json', 'w') as f:
            print(json.dumps(tail_fct_cdf), file=f)

        
        return
    