# %%
from turtledemo.chaos import plot
import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_excel('data_bezeq.xlsx')
print('fsfgdfgdfgdfgdfg')
#%%
x= df['מועד החיוב'].values
y = df['היקף הכנסה'].values
pairs = sorted(zip(x,y))

vec = dict(pairs)
plt.figure(figsize=(10,10))
df.plot(x='מועד החיוב',y='היקף הכנסה',kind='bar')
plt.show()