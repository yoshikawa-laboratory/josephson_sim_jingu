from typing_extensions import ParamSpec
from jinja2 import Template, Environment, FileSystemLoader
import os
import sys,subprocess

import numpy as np
import csv
import pandas as pd
import matplotlib.pyplot as plt
from decimal import Decimal
import argparse
import time

##description

def get_arg():
    parser = argparse.ArgumentParser(description="Automation about energy calc of aqfp")
    parser.add_argument('-f','--figure', default=False,type=bool, help='Default : false, if it true, save figure.')
    parser.add_argument('-n','--input_num',default=1,type=int, help='Default : 1, bit width of input.')
    parser.add_argument('-s','--sim',default="jsim",type=str, help='Default : jsim, jsim or josim241 or josim251.')
    parser.add_argument('-d','--dir',type=str, help='run_directory')
    parser.add_argument('-i','--input_filename',default='templete.inp',type=str, help='input_filename')
    parser.add_argument('-p','--parallel',default=0,type=int,help = 'Parallel run. Default is 0. Please use it carefully.')
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
    period = round(10**6/freq,1) # piko sec
    input_v =[]
    begin = period*10 +round(period/4 + 40,1)
    end = begin + period# piko sec
    for item in input:
        if(item == '1'):
            input_v.append("5m")
        if(item == '0'):
            input_v.append("-5m")    
    filename = f'{input}_{str(freq)}'
    out_file_name = filename +'.CSV'
    data= {"freq":str(freq),"input":input_v,"end":end,"out_file_name": out_file_name,"period":period,"begin":begin,"t_step":t_step,"sim":""}

    disp_text = template.render(data)

    with open(filename+'.inp','w') as f:
        f.write(disp_text)
        f.write("\n")
    return filename


def get_energy(filename:str,t_step:float=0.1):
    df = None
    if (args.sim =='jsim'):
        df = pd.read_csv(filename+".CSV",encoding = 'utf-8', sep=' ',header = None, index_col=0)
    else : # expect josim
        df = pd.read_csv(filename+".CSV",encoding = 'utf-8', sep=',',header = None, index_col=0 ,skiprows =1)
    if args.figure:
        df.plot(subplots=True)
        plt.savefig(filename+".png")
        plt.clf()
        plt.close()
    return [df[1].dot(df[2])*t_step*10**-12+df[3].dot(df[4])*t_step*10**-12,(df[1].dot(df[5]))*t_step*10**-12]


def freq_curve(input:str,freqs:list = [8000,5000,4000,2000,1000,800,640,500,400,320,200,160,125,100]):
    ene_list =[]
    input_filename = args.input_filename
    for item in freqs:
        filename = gene_netlist(input_filename,freq = item,input =input,t_step = 0.1)
        run_sim(filename)
        ene_list.append((item,get_energy(filename)))
        # remove .CSV and .inp
        os.remove(filename+".CSV")
        os.remove(filename+".inp")
    return ene_list

def run_sim(filename:str)->None:
    print(filename)
    if(args.sim=="jsim"):
        subprocess.run(["jsim_n",filename+'.inp'],stdout=subprocess.DEVNULL)
    else: # assume josim
        subprocess.run([args.sim,filename+'.inp'],stdout=subprocess.DEVNULL)
        

def main()->None:
    time_begin= time.time()

    os.chdir(args.dir)
    for i in range(int(2**args.input_num)):
        if i ==1:
            break
        input = format(i,f'0{args.input_num}b')
        ene_list = freq_curve(input = input)
        with open(f"energy_{input}_josim.csv",mode ='w') as f:
            print ("--- Freqency loop---")
            for item in ene_list:
                f.write(f'0b{input},{item[0]},{item[1][0]},{item[1][1]}\n')
    time_end = time.time()    
    print(f"Run time {time_end-time_begin} sec")


#### grobal parameter ####
args = get_arg()

if __name__ == "__main__":
    main()
