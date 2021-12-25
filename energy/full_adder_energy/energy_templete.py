from jinja2 import Template, Environment, FileSystemLoader
import os
import sys,subprocess

import numpy as np
import csv
import pandas as pd
import matplotlib.pyplot as plt
from decimal import Decimal


## description
def dot (left:list, right:list)->Decimal:
    lenght = len(left)
    ans = Decimal("0.00")
    for item in range(lenght):
        ans+= Decimal(str(left[item]))*Decimal(str(right[item]))*Decimal("1E-13")
    return ans


def gene_netlist(freq:int=5000, input:str= "11111",t_step:float = 0.1)-> str:
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('full_adder.inp')
    ##freq should be mega heltz
    period = round(10**6/freq,1) # piko sec
    input_v =[]
    begin = period*4 +round(period/4 + 50,1)
    end = begin + period# piko sec
    for item in input:
        if(item == '1'):
            input_v.append("5m")
        if(item == '0'):
            input_v.append("-5m")    
    filename = f'{input}_{str(freq)}'
    out_file_name = filename +'.CSV'
    # write netlist
    data= {"freq":str(freq),"input":input_v,"end":end,"out_file_name": out_file_name,"period":period,"begin":begin,"t_step":t_step}
    disp_text = template.render(data)
    with open(filename+'.inp','w') as f:
        f.write(disp_text)
        f.write("\n")
    return filename

def get_energy(filename:str,t_step:float=0.1):
    df = pd.read_csv(filename+".CSV",encoding = 'utf-8', sep=' ',header = None, index_col=0)
    df.plot(subplots=True)
    plt.savefig(filename+".png")
    # nannka kore ga nai to memory leak suru rashii
    plt.clf()
    plt.close()
    #
    return [df[1].dot(df[2])*t_step*10**-12+df[3].dot(df[4])*t_step*10**-12,df[1].dot(df[5])*t_step*10**-12,df[3].dot(df[6])*t_step*10**-12]


def freq_curve(input:str,freqs:list = [8000,5000,4000,2000,1000,800,640,500,400,320,200,160,125,100]):
    ene_list =[]
    for item in freqs:
        filename = gene_netlist(freq = item,input =input,t_step = 0.1)
        print(f'run {input},{item}')
        subprocess.run(["jsim_n",filename+'.inp'],stdout=subprocess.DEVNULL)
        ene_list.append((item,get_energy(filename)))
        # remove .CSV and .inp
        os.remove(filename+".CSV")
        #os.remove(filename+".inp")
    return ene_list


def main()->None:
    os.remove("result.CSV")
    for i in range(8):
        input = format(i,'03b')
        ene_list = freq_curve(input = input,freqs=[8000,4000,2000,1000,800,400,200,100])
        with open("result.CSV",mode="a") as f:
            for item in ene_list:
                f.write(f'{input},{item[0]},{item[1][0]},{item[1][1]},{item[1][2]}\n')


if __name__ == "__main__":
    main()
