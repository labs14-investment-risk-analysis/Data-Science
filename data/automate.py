from model import ModelMaker
import csv
import os

csv500 = open('sp500_data/sp500.csv', 'r')
sp500 = []
next(csv500)
for sym in csv.reader(csv500, delimiter=','):
    sp500.append(sym[0])

slices_se = [12,20]

lstm_layers = [[361, 196, 64], [300 ,200, 50]]
dropouts = [[0.2, 0.2, 0.2]]
l_rate = [.007, .025]
p = [0.001]
decay = [0.0001]
loss = ['mean_squared_logarithmic_error']
seq_length = [30]
batch_size = [15]
epochs = [30]

p_grid = {'lstm_layers':  lstm_layers,
          'dropouts':     dropouts,
          'l_rate':       l_rate,
          'p':            p,
          'decay':        decay,
          'loss':         loss,
          'seq_length':   seq_length,
          'batch_size':   batch_size,
          'epochs':       epochs
         }

save_directory = '/home/joe/Documents/automate_save'

for tkr_id in sp500[slices_se[0]:slices_se[1]]:
    mm = ModelMaker(tkr_id, save_directory)

    res, best = mm.fit_model(param_grid=p_grid)
    mm.get_shapley(best=best)
    mm.save_results(sk_results=res, sk_estimator=best)
