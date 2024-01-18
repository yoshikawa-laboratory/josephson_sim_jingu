#!/usr/bin/env python3
from readline import get_endidx
from typing import Tuple
from typing_extensions import ParamSpec
from jinja2 import Template, Environment, FileSystemLoader
import os
import sys,subprocess

import pandas as pd
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot
from decimal import Decimal
import argparse
import time
import logging
from logging import getLogger, StreamHandler, Formatter
from concurrent import futures
import numpy as np
import datetime
import math
from collections import deque
import json

##description

def get_arg():
    parser = argparse.ArgumentParser(description="Automation about energy calc of aqfp")
    parser.add_argument('-f','--figure', action='store_true',help='Default : false. This is flag')
    parser.add_argument('-n','--input_num',default=1,type=int, help='Default : 1, bit width of input.')
    parser.add_argument('-s','--sim',default="jsim",type=str, help='Default : jsim, jsim or josim241 or josim251.')
    parser.add_argument('-d','--dir',type=str, help='run_directory')
    parser.add_argument('-i','--input_filename',default='templete.inp',type=str, help='input_filename')
    parser.add_argument('-p','--parallel',default=1,type=int,help = 'Parallel run. Default is 1. Please use it carefully.')
    parser.add_argument('-r','--random',default=0,type=int,help = 'Default is 0. ')
    parser.add_argument('-q','--equation',default='equation.txt',type=str, help='equation it should calclulate')
    return parser.parse_args()

def dot (left:list, right:list)->Decimal:
    lenght = len(left)
    ans = Decimal("0.00")
    for item in range(lenght):
        ans+= Decimal(str(left[item]))*Decimal(str(right[item]))*Decimal("1E-13")
    return ans


def gene_netlist( input_filename:str,freq:int=5000, input:str= "11111",t_step:float = 0.1)-> str:
    #設定ファイル読み込み
    with open('netlist.config.json') as f:
        params = json.load(f)

    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(input_filename)
    ##freq should be mega heltz
    start_offset= 40
    period = round(10**6/freq,1) # piko sec
    input_v =[]
    begin = period*7 +round(period/4 + start_offset,1)
    end = begin + period# piko sec
    for item in input:
        if(item == '1'):
            input_v.append("5m")
        if(item == '0'):
            input_v.append("-5m")    
    filename = f'{input}_{str(freq)}'
    out_file_name = filename +'.CSV'
    data = {"freq":str(freq),"input":input_v,"end":end,"out_file_name": out_file_name,"period":period,"begin":begin,"t_step":t_step,"start_offset":start_offset}

    disp_text = template.render(params)

    with open(filename+'.inp','w') as f:
        f.write(disp_text)
        f.write("\n")
    return filename


def get_energy(filename:str,t_step:float=0.1):
    df = pd.read_csv(filename+".CSV",encoding = 'utf-8', sep=',',header = None, index_col=0 ,skiprows =1)


    if args.figure:
        df.plot(subplots=True)
        pyplot.savefig(filename+".png")
        pyplot.clf()
        pyplot.close('all')
    values = eval_equations(df,t_step)
    if any([math.isnan(item) for item in values]):
        pass
    else:
        os.remove(filename+".CSV")
        os.remove(filename+".inp")
    return values

def eval_equations(df : pd.DataFrame,t_step):
    result = []
    d = deque()
    with open(args.equation) as f:
        for line in f.readlines():
            for i,v in enumerate( line.split()):
                if(v =="*"):
                    num = (np.dot(d.pop(),d.pop())*t_step*10**-12 )
                    d.append(num)
                elif(v =="+"):
                    num = d.pop()+d.pop()
                    d.append(num)
                elif(v == "-"):
                    num = d.pop()-d.pop()
                    d.append(num)
                else:
                    d.append(df[int(v)])
            result.append(d.pop())

    return result
        


def gene_run_sim(input_vect:str,freq:int)->Tuple[str, int, str]:
    filename = gene_netlist(args.input_filename, freq=freq,input= input_vect,t_step= 0.1)
    run_sim(filename)
    return input_vect,freq,filename

def run_sim(filename:str)->None:
    logger.debug(f'run {filename}')
    if(args.sim=="jsim"):
        subprocess.run(["jsim_n",filename+'.inp'],stdout=subprocess.DEVNULL)
    else: # assume josim
        subprocess.run([args.sim,filename+'.inp'],stdout=subprocess.DEVNULL)
    logger.debug(f'finish {filename}')
        

def main()->None:
    time_begin= time.time()
    os.chdir(args.dir)
    freqs = [8000,5000,4000,2000,1000,800,640,500,400,320,200,160,125,100]
    # freqs = [8000,4000,2000,1000,500,400,320,200,100]
    future_result =[]
    input_vects = []
    if args.random == 0:
        input_vects = range(int(2**args.input_num))
    else:
        input_vects = sorted(set(list(np.random.randint(0,int(2**args.input_num),args.random))))
        logger.info(input_vects)
    logger.info("state 1")
    with futures.ThreadPoolExecutor(max_workers=args.parallel) as executor:
        for i,num in enumerate(input_vects):
            # if(i==50):
            #     break
            input_vect = format(num,f'0{args.input_num}b')
            for freq in freqs:
                future = executor.submit(gene_run_sim,input_vect,freq)
                future_result.append(future)
    time.sleep(10)
    logger.info("exporting simulation result")
    time_stamp = datetime.datetime.fromtimestamp(time.time())
    with open(f"energy_{args.sim}_{time_stamp.strftime('%m_%d_%H_%M_%S')}.csv",mode ='w') as f:
        for item in future_result:
            foo = item.result()
            energy = get_energy(foo[2])
            energy_str = ",".join([str(x) for x in energy])
            f.write(f'0b{foo[0]},{str(foo[1])},{energy_str}\n')
    logger.info("state 3")
    time_end = time.time()    
    logger.info(f"Run time {time_end-time_begin} sec")


#### grobal parameter ####
args = get_arg()

### log setting ### https://qiita.com/mimitaro/items/9fa7e054d60290d13bfc
logger = getLogger("Run log")
logger.setLevel(logging.DEBUG)
stream_handler = StreamHandler()
stream_handler.setLevel(logging.DEBUG)
handler_format = Formatter("[%(asctime)s - %(message)s]")
stream_handler.setFormatter(handler_format)
logger.addHandler(stream_handler)


if __name__ == "__main__":
    main()
