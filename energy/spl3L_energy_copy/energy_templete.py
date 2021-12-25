from jinja2 import Template, Environment, FileSystemLoader
import os
import sys,subprocess

import numpy as np
import csv
import pandas as pd
import matplotlib.pyplot as plt
from decimal import Decimal


##description

def dot (left:list, right:list)->Decimal:
    lenght = len(left)
    ans = Decimal("0.00")
    for item in range(lenght):
        ans+= Decimal(str(left[item]))*Decimal(str(right[item]))*Decimal("1E-13")
    return ans


def gene_netlist(freq:int=5000, input:str= "11111")-> str:
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('spl3L_energy.inp')
    ##freq should be mega heltz
    period = round(10**6/freq,1) # piko sec
    input_v =[]
    begin = period*4 +round(period/4 + 50,1)+0.1
    end = begin + period -0.1# piko sec
    for item in input:
        if(item == '1'):
            input_v.append("5m")
        if(item == '0'):
            input_v.append("-5m")    
    filename = f'{input}_{str(freq)}'
    out_file_name = filename +'.CSV'
    data= {"freq":str(freq),"input":input_v,"end":end,"out_file_name": out_file_name,"period":period,"begin":begin}

    disp_text = template.render(data)

    with open(filename+'.inp','w') as f:
        f.write(disp_text)
        f.write("\n")
    return filename


def get_energy(filename:str):
    df = pd.read_csv(filename+".CSV",encoding = 'utf-8', sep=' ',header = None, index_col=0)
    df.plot(subplots=True)
    plt.savefig(filename+".png")
    plt.clf()
    plt.close()
    return [df[1].dot(df[2])*1*10**-13,(df[3].dot(df[4]))*1*10**-13,(df[1].dot(df[5]))*1*10**-13]

freqs = [8000,5000,4000,2000,1000,800,640,500,400,320,200,160,125,100]
ene_list =[]
for item in freqs:
    filename = gene_netlist(freq = item,input ="10101")
    subprocess.run(["jsim_n",filename+'.inp'],stdout=subprocess.DEVNULL)
    ene_list.append(get_energy(filename))

for i,item in enumerate(ene_list):
    print(f'{freqs[i]},{item[0]},{item[1]},{item[2]}')


