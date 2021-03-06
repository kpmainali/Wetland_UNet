# -*- coding: utf-8 -*-
"""
Created on Tue Jun 22 15:52:39 2021

@author: MEvans
"""

# -*- coding: utf-8 -*-
"""
Created on Wed May  5 12:10:06 2021

@author: MEvans
"""

# -*- coding: utf-8 -*-
"""
Created on Sat Jan  2 12:41:40 2021

@author: MEvans
"""

from Satellite_ComputerVision import model_tools, processing
from Satellite_ComputerVision.prediction_tools import makePredDataset, callback_predictions, plot_to_image
from matplotlib import pyplot as plt
import argparse
import os
import glob
import json
import math
import tensorflow as tf
from datetime import datetime
from azureml.core import Run, Workspace, Model


# Set Global variables

parser = argparse.ArgumentParser()
parser.add_argument('--train_data', type = str, required = True, help = 'Training datasets')
parser.add_argument('--eval_data', type = str, required = True, help = 'Evaluation datasets')
parser.add_argument('--test_data', type = str, default = None, help = 'directory containing test image(s) and mixer')
parser.add_argument('--model_id', type = str, required = False, default = None, help = 'model id for continued training')
parser.add_argument('-lr', '--learning_rate', type = float, default = 0.001, help = 'Initial learning rate')
parser.add_argument('-w', '--weight', type = float, default = 1.0, help = 'Positive sample weight for iou, bce, etc.')
parser.add_argument('--bias', type = float, default = None, help = 'bias value for keras output layer initializer')
parser.add_argument('-e', '--epochs', type = int, default = 10, help = 'Number of epochs to train the model for')
parser.add_argument('-b', '--batch', type = int, default = 16, help = 'Training batch size')
parser.add_argument('--size', type = int, default = 3000, help = 'Size of training dataset')
parser.add_argument('--kernel_size', type = int, default = 256, dest = 'kernel_size', help = 'Size in pixels of incoming patches')
parser.add_argument('--response', type = str, required = True, help = 'Name of the response variable in tfrecords')
parser.add_argument('--bands', type = str, nargs = '+', required = False, default = ['B3_summer', 'B3_fall', 'B3_spring', 'B4_summer', 'B4_fall', 'B4_spring', 'B5_summer', 'B5_fall', 'B5_spring', 'B6_summer', 'B6_fall', 'B6_spring', 'B8_summer', 'B8_fall', 'B8_spring', 'B11_summer', 'B11_fall', 'B11_spring', 'B12_summer', 'B12_fall', 'B12_spring', 'R', 'G', 'B', 'N', 'lidar_intensity', 'geomorphons'])
parser.add_argument('--splits', type = int, nargs = '+', required = False, default = None )
parser.add_argument('--one_hot_levels', type = int, nargs = '+', required = False, default = [11])
parser.add_argument('--one_hot_names', type = str, nargs = '+', required = False, default = ['geomorphons'])
args = parser.parse_args()

ONE_HOT = dict(zip(args.one_hot_names, args.one_hot_levels))
SPLITS = args.splits
TRAIN_SIZE = args.size
BATCH = args.batch
EPOCHS = args.epochs
BIAS = args.bias
WEIGHT = args.weight
LR = args.learning_rate
BANDS = args.bands
RESPONSE = args.response
OPTIMIZER = tf.keras.optimizers.Adam(learning_rate=LR, beta_1=0.9, beta_2=0.999)
DEPTH = len(BANDS)+sum(args.one_hot_levels)-len(args.one_hot_levels)
print(BANDS)

METRICS = {
        'logits':[tf.keras.metrics.MeanSquaredError(name='mse'), tf.keras.metrics.Precision(name='precision'), tf.keras.metrics.Recall(name='recall')],
        'classes':[tf.keras.metrics.MeanIoU(num_classes=2, name = 'mean_iou')]
        }

FEATURES = BANDS + [RESPONSE]

# round the training data size up to nearest 100 to define buffer
BUFFER = math.ceil(args.size/100)*100

# Specify the size and shape of patches expected by the model.
KERNEL_SIZE = args.kernel_size
KERNEL_SHAPE = [KERNEL_SIZE, KERNEL_SIZE]
COLUMNS = [
  tf.io.FixedLenFeature(shape=KERNEL_SHAPE, dtype=tf.float32) for k in FEATURES
]
FEATURES_DICT = dict(zip(FEATURES, COLUMNS))

# create special folders './outputs' and './logs' which automatically get saved
os.makedirs('outputs', exist_ok = True)
os.makedirs('logs', exist_ok = True)
out_dir = './outputs'
log_dir = './logs'

# create training dataset

# train_files = glob.glob(os.path.join(args.data_folder, 'training', 'UNET_256_[A-Z]*.gz'))
# eval_files =  glob.glob(os.path.join(args.data_folder, 'eval', 'UNET_256_[A-Z]*.gz'))
i = 1
train_files = []
for root, dirs, files in os.walk(args.train_data):
    for f in files:
        if i%2==0:
            train_files.append(os.path.join(root, f))
        i+=1
i = 1
eval_files = []
for root, dirs, files in os.walk(args.eval_data):
    for f in files:
        if i%2==0:
            eval_files.append(os.path.join(root, f))
        i+=1
        
# train_files = glob.glob(os.path.join(args.train_data, 'UNET_256_[A-Z]*.gz'))
# eval_files =  glob.glob(os.path.join(args.eval_data, 'UNET_256_[A-Z]*.gz'))

training = processing.get_training_dataset(
        files = train_files,
        ftDict = FEATURES_DICT,
        features = BANDS,
        response = RESPONSE,
        buff = BUFFER,
        batch = BATCH,
        repeat = True,
        splits = SPLITS,
        one_hot = ONE_HOT)

evaluation = processing.get_eval_dataset(
        files = eval_files,
        ftDict = FEATURES_DICT,
        features = BANDS,
        response = RESPONSE,
        splits = SPLITS,
        one_hot = ONE_HOT)

## DEFINE CALLBACKS

def get_weighted_bce(y_true, y_pred):
    return model_tools.weighted_bce(y_true, y_pred, WEIGHT)

# get the current time
now = datetime.now() 
date = now.strftime("%d%b%y")
date

# define a checkpoint callback to save best models during training
checkpoint = tf.keras.callbacks.ModelCheckpoint(
    os.path.join(out_dir, 'best_weights_' + date + '.hdf5'),
    monitor='val_mean_iou',
    verbose=1,
    save_best_only=True,
    mode='max'
    )

# define a tensorboard callback to write training logs
tensorboard = tf.keras.callbacks.TensorBoard(log_dir = log_dir)

# get the run context
run = Run.get_context()
exp = run.experiment
ws = exp.workspace

## BUILD THE MODEL
# Create a MirroredStrategy.
strategy = tf.distribute.MirroredStrategy()
print('Number of devices: {}'.format(strategy.num_replicas_in_sync))

# we will package the 'models' directory within the 'azure' dirrectory submitted with experiment run
model_dir = Model.get_model_path(args.model_id, _workspace = ws)
#    model_dir = os.path.join('./models', args.model_id, '1', 'outputs')
METRICS = {
        'logits':[tf.keras.metrics.MeanSquaredError(name='mse'), tf.keras.metrics.Precision(name='precision'), tf.keras.metrics.Recall(name='recall')],
        'classes':[tf.keras.metrics.MeanIoU(num_classes=2, name = 'mean_iou')]
}
# load our previously trained model and weights
model_file = glob.glob(os.path.join(model_dir, '*.h5'))[0]
weights_file = glob.glob(os.path.join(model_dir, '*.hdf5'))[0]
m, checkpoint = model_tools.retrain_model(model_file, checkpoint, evaluation, 'classes_mean_iou', weights_file, weight = WEIGHT, lr = LR)
# TEMPORARILY ADD CODE TO ADD A CLASS OUTPUT TO MODELS
#logits = m.outputs[0]
#logits._name='logits'
#classes = tf.keras.layers.Lambda(lambda x: tf.cast(tf.greater(x, 0.5), dtype = tf.int32), name = 'classes')(logits)
#m2 = tf.keras.models.Model(m.input, [logits, classes])
#m2.compile(
#        optimizer = m.optimizer,
#        loss = m.loss,
#        metrics = METRICS)
# TODO: make this dynamic
initial_epoch = 100

# if test images provided, define an image saving callback
if args.test_data:
    
    test_files = glob.glob(os.path.join(args.test_data, '*.gz'))
    mixer_file = glob.glob(os.path.join(args.test_data, '*.json'))
    
    # run predictions on a test image and log so we can see what the model is doing at each epoch
    jsonFile = mixer_file[0]
    with open(jsonFile,) as file:
        mixer = json.load(file)
        
    pred_data = makePredDataset(test_files, BANDS, one_hot = ONE_HOT)
    file_writer = tf.summary.create_file_writer(log_dir + '/preds')

    def log_pred_image(epoch, logs):
      out_image = callback_predictions(pred_data, m, mixer)
      prob = out_image[:, :, 0]
      figure = plt.figure(figsize=(10, 10))
      plt.imshow(prob)
      image = plot_to_image(figure)
    
      with file_writer.as_default():
        tf.summary.image("Predicted Image", image, step=epoch)
    
    pred_callback = tf.keras.callbacks.LambdaCallback(on_epoch_end = log_pred_image)
    
    callbacks = [checkpoint, tensorboard, pred_callback]
else:
    callbacks = [checkpoint, tensorboard]
    
# train the model
steps_per_epoch = int(TRAIN_SIZE//BATCH)
print(steps_per_epoch)
m.fit(
        x = training,
        epochs = EPOCHS,
        steps_per_epoch = steps_per_epoch,
        validation_data = evaluation,
        callbacks = callbacks#,
        #initial_epoch = initial_epoch
        )

m.save(os.path.join(out_dir, 'unet256.h5'))
