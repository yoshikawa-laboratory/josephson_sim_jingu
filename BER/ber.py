#!/usr/bin/env python3
from typing import Tuple
from jinja2 import Environment, FileSystemLoader
import os
import subprocess

import matplotlib
matplotlib.use('Agg')
import argparse
import time
import logging
from logging import getLogger, StreamHandler, Formatter
from concurrent import futures
import numpy as np
import datetime
import json

import pandas as pd


##description

def get_arg():
    parser = argparse.ArgumentParser(description="Automation about energy calc of aqfp")
    parser.add_argument('-d','--dir',type=str, help='run_directory')
    parser.add_argument('-s','--source_file',default='netlist.spice',type=str, help='source_file')
    return parser.parse_args()


def gene_netlist( source_netlist:str,tr_len:str,imp:str)-> str:
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(source_netlist)
  
    filename = f'{source_netlist}_{tr_len}_{imp}'
    out_file_name = filename +'.CSV'
    #設定ファイル読み込み
    with open('netlist_config.json') as f:
        params = json.load(f)
    params |= {"out_file_name": out_file_name,"delay": tr_len, "imp" :str(imp)}

    generated_netlist = template.render(params)

    with open(filename+'.inp','w') as f:
        f.write(generated_netlist)
        f.write("\n")
    return filename

def gene_run_sim(tr_len:str,imp:str)->Tuple[str,str]:
    filename = gene_netlist(str(args.source_file),tr_len,imp)
    run_sim(filename)
    return tr_len,imp,filename

def run_sim(filename:str)->None:
    logger.debug(f'run {filename}')
    subprocess.run(["josim_v265",filename+'.inp','-m'],stdout=subprocess.DEVNULL)

def get_data(data: pd.DataFrame, dt:float, period:float,begin:float):
    start = int(begin/dt)
    step = int(period/dt)
    return data.iloc[start:None:step].copy()

def binarization(data:pd.Series, th_1:float=1e-6, th_0:float = -1*1e-6):
    data.loc[data<th_0] = 0
    data.loc[data>th_1] = 1


def eval_result(csv_filename:str)->float:
    df  = pd.read_csv(csv_filename+".CSV",index_col = 0)
    dt = float(df.index[1]- df.index[0])
    input = get_data(df["I(R0)"],dt,200*10**-12, 100*10**-12)
    data = get_data(df["I(LQ|XI7)"],dt,200*10**-12, 240*10**-12)
    binarization(input, 0,0)
    binarization(data,0,0)
    return np.count_nonzero(data.values[1:] !=input.values[0:-2])/len(data.values[1:])
    pass

        

def main()->None:
    time_begin= time.time()
    os.chdir(args.dir)
    future_result =[]
    imp_lists = [2,4,6,8,10,12,14,16,18]
    tr_line_lengths = list(np.arange(1,10,0.1))
    logger.info("state 1")
    with futures.ThreadPoolExecutor(max_workers=60) as executor:
        for imp in [str(x) for x in imp_lists]:
            for tr_len in [str(round(x,2)) for x in tr_line_lengths]:
                future = executor.submit(gene_run_sim,tr_len=tr_len,imp=imp)
                future_result.append(future)
    logger.info("exporting simulation result")
    time_stamp = datetime.datetime.fromtimestamp(time.time())
    with open(f"BER_{time_stamp.strftime('%m_%d_%H_%M_%S')}.csv",mode ='w') as f:
        for item in future_result:
            tr_len,imp,file_name = item.result()
            ber = eval_result(file_name)
            f.write(f'{tr_len},{imp},{ber}\n')
            print(f'{tr_len},{imp},{ber}')
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
