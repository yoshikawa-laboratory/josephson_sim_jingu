#!/usr/bin/env python3
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

##description

def get_arg():
    parser = argparse.ArgumentParser(description="Automation about energy calc of aqfp")
    parser.add_argument('-f','--figure', action='store_true',help='Default : false. This is flag')
    parser.add_argument('-n','--input_num',default=1,type=int, help='Default : 1, bit width of input.')
    parser.add_argument('-s','--sim',default="jsim",type=str, help='Default : jsim, jsim or josim241 or josim251.')
    parser.add_argument('-d','--dir',type=str, help='run_directory')
    parser.add_argument('-i','--input_filename',default='templete.inp',type=str, help='input_filename')
    parser.add_argument('-p','--parallel',default=0,type=int,help = 'Parallel run. Default is 0. Please use it carefully.')
    parser.add_argument('-r','--random',default=0,type=int,help = 'Default is 0. ')
    return parser.parse_args()

def dot (left:list, right:list)->Decimal:
    lenght = len(left)
    ans = Decimal("0.00")
    for item in range(lenght):
        ans+= Decimal(str(left[item]))*Decimal(str(right[item]))*Decimal("1E-13")
    return ans


def gene_netlist( input_filename:str,freq:int=5000, input:str= "11111",t_step:float = 0.1)-> str:
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(input_filename)
    ##freq should be mega heltz
    start_offset= 40
    period = round(10**6/freq,1) # piko sec
    input_v =[]
    begin = period*10 +round(period/4 + start_offset,1)
    end = begin + period# piko sec
    for item in input:
        if(item == '1'):
            input_v.append("5m")
        if(item == '0'):
            input_v.append("-5m")    
    filename = f'{input}_{str(freq)}'
    out_file_name = filename +'.CSV'
    data = {"freq":str(freq),"input":input_v,"end":end,"out_file_name": out_file_name,"period":period,"begin":begin,"t_step":t_step,"start_offset":start_offset}

    disp_text = template.render(data)

    with open(filename+'.inp','w') as f:
        f.write(disp_text)
        f.write("\n")
    return filename


def get_energy(filename:str,t_step:float=0.1):
    df = None
    try:
        if (args.sim =='jsim'):
            df = pd.read_csv(filename+".CSV",encoding = 'utf-8', sep=' ',header = None, index_col=0)
        else : # expect josim
            df = pd.read_csv(filename+".CSV",encoding = 'utf-8', sep=',',header = None, index_col=0 ,skiprows =1)
    except:
        logger.error(f'josim run error at {filename}')    
        return [np.nan,np.nan] 

    if args.figure:
        df.plot(subplots=True)
        pyplot.savefig(filename+".png")
        pyplot.clf()
        pyplot.close('all')
    energy_ac1 = df[1].dot(df[2])*t_step*10**-12
    energy_ac2 = df[3].dot(df[4])*t_step*10**-12
    energy_ac1_DUT = (df[1].dot(df[5]))*t_step*10**-12
    energy_ac2_DUT =0.0 if len(df.columns)<6 else (df[3].dot(df[6]))*t_step*10**-12
    return [energy_ac1+energy_ac2,energy_ac1_DUT+energy_ac2_DUT]


def calc_energy(input_vect:str,freq:int):
    filename = gene_netlist(args.input_filename, freq=freq,input= input_vect,t_step= 0.1)
    run_sim(filename)
    energy = get_energy(filename)
    os.remove(filename+".CSV")
    os.remove(filename+".inp")
    return input_vect,freq,energy

def run_sim(filename:str)->None:
    logger.debug(f'run {filename}')
    if(args.sim=="jsim"):
        subprocess.run(["jsim_n",filename+'.inp'],stdout=subprocess.DEVNULL)
    else: # assume josim
        subprocess.run([args.sim,filename+'.inp'],stdout=subprocess.DEVNULL)
        

def main()->None:
    time_begin= time.time()
    os.chdir(args.dir)
    #freqs = [8000,5000,4000,2000,1000,800,640,500,400,320,200,160,125,100]
    freqs = [8000,4000,2000,1000,500,400,320,200,100]
    future_result =[]
    input_vects = []
    if args.random == 0:
        input_vects = range(int(2**args.input_num))
    else:
        input_vects = np.random.randint(0,int(2**args.input_num),args.random)
        print(input_vects)
    with futures.ThreadPoolExecutor(max_workers=25) as executor:
        for i,num in enumerate(input_vects):
            #if(i==5):
            #    break
            input_vect = format(num,f'0{args.input_num}b')
            for freq in freqs:
                future = executor.submit(calc_energy,input_vect,freq)
                future_result.append(future)
    with open(f"energy_{args.sim}.csv",mode ='w') as f:
        for item in future_result:
            foo = item.result()
            f.write(f'0b{foo[0]},{str(foo[1])},{foo[2][0]},{foo[2][1]}\n')
    time_end = time.time()    
    print(f"Run time {time_end-time_begin} sec")


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
