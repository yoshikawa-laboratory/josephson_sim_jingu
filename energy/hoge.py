import os
from readline import get_endidx
import sys

sys.path.append('../')
import energy.calc_energy as calc_energy
answer = []
input_vects = range(int(2**8))
freqs = [8000,4000,2000,1000,500,400,320,200,100]
for num in input_vects:
    for freq in freqs:
        bin_num = format(num,'08b')
        enrgy = calc_energy.get_energy(f'{bin_num}_{freq}')
        answer.append([freq,bin_num,enrgy[0],enrgy[1]])



with open("foooo.csv",mode ='w') as f:
    for item in answer:
        f.write(f'0b{item[1]},{item[0]},{item[2]},{item[3]}\n')