# -*- coding: utf-8 -*-
"""GAN

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1kgBo39XjLvXep_r0ZhHX2PmgXj72Tu1J
"""

#!mkdir data midi_songs midi_songs/new_game_music

import glob
import pickle
import numpy
#!pip install music21
from music21 import instrument, note, stream, chord, converter, duration
from keras.utils import np_utils
from keras.callbacks import ModelCheckpoint
import keras
import tensorflow as tf
#import numpy as np

# Configuration
songs = glob.glob("game_songs/*.mid")
TIMESTEP = 0.25
SEQUENCE_LEN = int(8 / TIMESTEP)
NUM_EPOCHS = 200
MODEL_NAME = f'gan-transposed-nulls-variableLength-new-game-music{len(songs)}-e{NUM_EPOCHS}-s{SEQUENCE_LEN}'

# GAN constants
NOISE_SIZE = 33
HISTORY_LENGTH = 32
#GENERATOR_OUTPUT_SIZE = ??????? # size of the vocabulary dictionary

class Trainer:
    def __init__(self, model_name, songs):
        self.model_name = model_name
        self.songs = songs
        self.model = None

    def train_network(self):
        """ Train a Neural Network to generate music """
        notes = self.get_notes()
        #with open('data/notes', 'rb') as filepath:
        #    notes = pickle.load(filepath)
        # get amount of pitch names
        n_vocab = len(set(notes))
        print('n_vocab', n_vocab)

        network_input, network_output = self.prepare_sequences(notes, n_vocab)

        self.discriminator, self.generator, self.combined_system = create_network(network_input, n_vocab)
        
        #t.generator.load_weights("gan-transposed-nulls-variableLength-new-game-music5-e2000-s32-weights-improvement-batch940-0.1942-bigger.hdf5")
        #t.discriminator.load_weights("gan-transposed-nulls-variableLength-new-game-music5-e2000-s32-weights-improvement-batch940-0.1942-bigger.hdf5")
        #t.combined_system.load_weights("gan-transposed-nulls-variableLength-new-game-music5-e2000-s32-weights-improvement-batch940-2.1764-bigger.hdf5")
        
        self.train(network_input, network_output)
        #file_name = self.model_name + '.hdf5'
        self.discriminator.save(self.model_name + '_discriminator' + '.hdf5')
        self.generator.save(self.model_name + '_generator' + '.hdf5')
        self.combined_system.save(self.model_name + '_combined_system' + '.hdf5')
        print(f'Model saved to {self.model_name}')

    def get_notes(self):
        """ Get all the notes and chords from the midi files in the ./midi_songs directory """
        notes = []

        for file in self.songs:
            print("Parsing %s" % file)
            try:
                midi = converter.parse(file)
            except IndexError as e:
                print(f'Could not parse {file}')
                print(e)
                continue
                
            notes_to_parse = None

            try: # file has instrument parts
                s2 = instrument.partitionByInstrument(midi)
                notes_to_parse = s2.parts[0].recurse() 
            except: # file has notes in a flat structure
                notes_to_parse = midi.flat.notes

            prev_offset = 0.0
            for element in notes_to_parse:
                if isinstance(element, note.Note) or isinstance(element, chord.Chord):
                    duration = element.duration.quarterLength
                    if isinstance(element, note.Note):
                        name = element.pitch
                    elif isinstance(element, chord.Chord):
                        name = '.'.join(str(n) for n in element.normalOrder)
                    notes.append(f'{name}${duration}')
                                               
                    rest_notes = int((element.offset - prev_offset) / TIMESTEP - 1)
                    for _ in range(0, rest_notes):
                        notes.append('NULL')  
                                               
                prev_offset = element.offset

        print('notes', notes)
        
        with open('data/notes', 'wb') as filepath:
            pickle.dump(notes, filepath)

        return notes

    def prepare_sequences(self, notes, n_vocab):
        """ Prepare the sequences used by the Neural Network """
        # get all pitch names
        pitchnames = sorted(set(item for item in notes))

         # create a dictionary to map pitches to integers
        note_to_int = dict((note, number + 1) for number, note in enumerate(pitchnames))
        note_to_int['NULL'] = 0

        network_input = []
        network_output = []

        # create input sequences and the corresponding outputs
        for i in range(0, len(notes) - SEQUENCE_LEN, 1):
            sequence_in = notes[i:i + SEQUENCE_LEN]
            sequence_out = notes[i + SEQUENCE_LEN]
            network_input.append([note_to_int[char] for char in sequence_in])
            network_output.append(note_to_int[sequence_out])

        n_patterns = len(network_input)

        # reshape the input into a format compatible with LSTM layers
        network_input = numpy.reshape(network_input, (n_patterns, SEQUENCE_LEN, 1))
        # normalize input
        network_input = network_input / float(n_vocab)
        
        network_output = np_utils.to_categorical(network_output)

        return (network_input, network_output)

    def train(self, network_input, network_output):
        """ train the neural network """
        
        # This is the old training method
        # self.model.fit(network_input, network_output, epochs=NUM_EPOCHS, batch_size=64, callbacks=callbacks_list)
        
        TRAINING_INPUT_SIZE = 1024
        
        if TRAINING_INPUT_SIZE > len(network_input):
           raise ValueError("That's not a big enough network_input for this training input size")
        #print ("shape out = ", network_output.shape)
        # This is the GAN training
        for batch in range(NUM_EPOCHS):
          print ("batch counter = " + str(batch))
          
          batch_training_input_start = numpy.random.randint(0, len(network_input) - TRAINING_INPUT_SIZE)
          batch_training_input = network_input[batch_training_input_start : batch_training_input_start + TRAINING_INPUT_SIZE]
          batch_network_output = network_output[batch_training_input_start : batch_training_input_start + TRAINING_INPUT_SIZE]
          if batch % 100 == 0:
            self.discriminator.save(self.model_name + "-batch" + str(batch) + '_discriminator' + '.hdf5')
            self.generator.save(self.model_name + "-batch" + str(batch) + '_generator' + '.hdf5')
            self.combined_system.save(self.model_name + "-batch" + str(batch) + '_combined_system' + '.hdf5')
        
          random_inputs_train = numpy.random.normal(size=[TRAINING_INPUT_SIZE, NOISE_SIZE])

          # Get generated data for the discriminator to work with
          generator_input = []
          for i in range(TRAINING_INPUT_SIZE):
              generator_input.append(numpy.concatenate([numpy.reshape(batch_training_input[i], (HISTORY_LENGTH,)), random_inputs_train[i]]))
          generator_input = numpy.array(generator_input)
          
          generated_patterns = self.generator.predict(generator_input)
          
          real_patterns = []
          #print ("out = ", network_output[0])
          for i in range(TRAINING_INPUT_SIZE):
            real_patterns.append(numpy.concatenate([numpy.reshape(batch_training_input[i], (HISTORY_LENGTH,)), batch_network_output[i]]))
          real_patterns = numpy.array(real_patterns)
          
          discriminator_inputs = numpy.concatenate([generated_patterns, real_patterns])
          label_noise_dev = 0.1
          ones = numpy.ones([TRAINING_INPUT_SIZE, 1])
          zeros = numpy.zeros([TRAINING_INPUT_SIZE, 1])
          discriminator_outputs = numpy.concatenate([ones, zeros])
          
          # Training the discriminator
          self.discriminator.fit(discriminator_inputs, discriminator_outputs, epochs=1)
          
          # Training the generator using the combined system
          desired_outputs_train = numpy.zeros([TRAINING_INPUT_SIZE, 1])
          self.combined_system.fit(generator_input, desired_outputs_train, epochs=1)


from keras.models import Sequential
from keras.layers import Dense
from keras.layers import Dropout
from keras.layers import LSTM
from keras.layers import Activation
from keras.layers import Bidirectional
from keras.layers import GaussianNoise

def create_network(network_input, n_vocab):

    
    TOTAL_HISTORY_SIZE = HISTORY_LENGTH
    
    # Defining generator
    generator_input = keras.layers.Input((TOTAL_HISTORY_SIZE + NOISE_SIZE,))
    
    def get_history(x):
      return keras.backend.slice(x, (0, 0), (-1, TOTAL_HISTORY_SIZE))
    history_storage = keras.layers.Lambda(get_history, output_shape=(TOTAL_HISTORY_SIZE,))(generator_input)
    
    g = keras.layers.Dense(TOTAL_HISTORY_SIZE * 4)(generator_input)
    g = keras.layers.Dropout(0.3)(g)
    g = keras.layers.LeakyReLU(alpha=0.2)(g)
    g = keras.layers.Dense(TOTAL_HISTORY_SIZE * 4)(g) 
    g = keras.layers.Dropout(0.3)(g)
    g = keras.layers.LeakyReLU(alpha=0.2)(g)
    g = keras.layers.Dense(n_vocab, activation="tanh")(g)         #doing this to keep values in range (0, 1)
    generator_output = keras.layers.concatenate([history_storage, g])
    
    # Defining discriminator
    discriminator_input = keras.layers.Input((TOTAL_HISTORY_SIZE + n_vocab,))         #this matches up with the output layer of the generator
    # put gaussian noise here to make the discriminator worse if it is too good for the generator
    x = keras.layers.GaussianNoise(0.5)(discriminator_input)
    x = keras.layers.Dense(TOTAL_HISTORY_SIZE + n_vocab)(x)
    x = keras.layers.Dropout(0.3)(x)
    x = keras.layers.LeakyReLU(alpha=0.2)(x)
    x = keras.layers.Dense(2, activation=tf.nn.softmax)(x)
    
    # Creating the models from the layers
    generator = keras.Model(inputs=generator_input, outputs = generator_output)
    discriminator = keras.Model(inputs=discriminator_input, outputs=x)
    
    # Have to compile the discriminator separately here
    discriminator.compile(optimizer=keras.optimizers.Adam(lr=0.00001), 
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])
    
    # Set discriminator to not be trainable before we compile it onto the end of the generator
    discriminator.trainable = False
    
    # Define full competitive system
    combined_system = keras.Sequential()
    combined_system.add(generator)
    combined_system.add(discriminator)
    combined_system.compile(optimizer=keras.optimizers.Adam(lr=0.0001), 
                            loss='sparse_categorical_crossentropy',
                            metrics=['accuracy'])
    
    return discriminator, generator, combined_system

t = Trainer(MODEL_NAME, songs)
t.train_network()

class Generator:
    def __init__(self, generator_weights):
        self.generator_weights = generator_weights

    def generate(self):
        """ Generate a piano midi file """
        #load the notes used to train the model
        with open('data/notes', 'rb') as filepath:
            notes = pickle.load(filepath)

        # Get all pitch names
        pitchnames = sorted(set(item for item in notes))
        # Get all pitch names
        n_vocab = len(set(notes))
        network_input, normalized_input = self.prepare_sequences(notes, pitchnames, n_vocab)
        
        discriminator, generator, combined_system = create_network(normalized_input, n_vocab)
        generator.load_weights(self.generator_weights)
        
        prediction_output = self.generate_notes(generator, network_input, pitchnames, n_vocab)
        print("prediction_output", prediction_output)
        self.create_midi(prediction_output)

    def prepare_sequences(self, notes, pitchnames, n_vocab):
        """ Prepare the sequences used by the Neural Network """
        # map between notes and integers and back
        note_to_int = dict((note, number + 1) for number, note in enumerate(pitchnames))
        note_to_int['NULL'] = 0


        network_input = []
        output = []
        for i in range(0, len(notes) - SEQUENCE_LEN, 1):
            sequence_in = notes[i:i + SEQUENCE_LEN]
            sequence_out = notes[i + SEQUENCE_LEN]
            network_input.append([note_to_int[char] for char in sequence_in])
            output.append(note_to_int[sequence_out])

        n_patterns = len(network_input)

        # reshape the input into a format compatible with LSTM layers
        normalized_input = numpy.reshape(network_input, (n_patterns, SEQUENCE_LEN, 1))
        # normalize input
        normalized_input = normalized_input / float(n_vocab)

        return (network_input, normalized_input)

    
    def generate_notes(self, model, network_input, pitchnames, n_vocab):
        """ Generate notes from the neural network based on a sequence of notes """
        int_to_note = dict((number + 1, note) for number, note in enumerate(pitchnames))
        int_to_note[0] = 'NULL'

        
        def get_start():
          # pick a random sequence from the input as a starting point for the prediction
          start = numpy.random.randint(0, len(network_input)-1)
          pattern = network_input[start]
          prediction_output = []
          return pattern, prediction_output
        
        def get_generator_input(verse_pattern):
            prediction_input = numpy.reshape(verse_pattern, (len(verse_pattern),))
            prediction_input = prediction_input / float(n_vocab)

            # Need some noise for the generator
            noise = numpy.random.normal(size=(NOISE_SIZE,))
            #print (noise)
            #print (prediction_input)
            prediction_input = numpy.concatenate([prediction_input, noise])
            prediction_input = numpy.reshape(prediction_input, (1, len(prediction_input)))
            #print (prediction_input)
            #print (prediction_input.shape)
            prediction = model.predict(prediction_input, verbose=0)
            prediction = prediction[0][HISTORY_LENGTH:]
            #print ("prediction", prediction)
            return prediction
          
        # generate verse 1
        verse1_pattern, verse1_prediction_output = get_start()
        for note_index in range(4 * SEQUENCE_LEN):

            prediction = get_generator_input(verse1_pattern)
            
            index = numpy.argmax(prediction)
            print('index', index)
            result = int_to_note[index]
            verse1_prediction_output.append(result)

            verse1_pattern.append(index)
            verse1_pattern = verse1_pattern[1:len(verse1_pattern)]
        
        
        # generate verse 2
        verse2_pattern = verse1_pattern
        verse2_prediction_output = []
        for note_index in range(4 * SEQUENCE_LEN):

            prediction = get_generator_input(verse2_pattern)
            
            index = numpy.argmax(prediction)
            print('index', index)
            result = int_to_note[index]
            verse2_prediction_output.append(result)

            verse2_pattern.append(index)
            verse2_pattern = verse2_pattern[1:len(verse2_pattern)]

        # generate chorus
        chorus_pattern, chorus_prediction_output = get_start()
        for note_index in range(4 * SEQUENCE_LEN):

            prediction = get_generator_input(chorus_pattern)

            index = numpy.argmax(prediction)
            print('index', index)
            result = int_to_note[index]
            chorus_prediction_output.append(result)

            chorus_pattern.append(index)
            chorus_pattern = chorus_pattern[1:len(chorus_pattern)]

        # generate bridge
        bridge_pattern, bridge_prediction_output = get_start()
        for note_index in range(4 * SEQUENCE_LEN):

            prediction = get_generator_input(bridge_pattern)
            
            index = numpy.argmax(prediction)
            print('index', index)
            result = int_to_note[index]
            bridge_prediction_output.append(result)

            bridge_pattern.append(index)
            bridge_pattern = bridge_pattern[1:len(bridge_pattern)]

        return (
            verse1_prediction_output
            + chorus_prediction_output
            + verse2_prediction_output
            + chorus_prediction_output
            + bridge_prediction_output
            + chorus_prediction_output
        )


    def create_midi(self, prediction_output):
        """ convert the output from the prediction to notes and create a midi file
            from the notes """
        offset = 0
        output_notes = []

        # create note and chord objects based on the values generated by the model
        for pattern in prediction_output:
            if '$' in pattern:
                pattern, dur = pattern.split('$')
                if '/' in dur:
                    a, b = dur.split('/')
                    dur = float(a) / float(b)
                else:
                    dur = float(dur)
                
            # pattern is a chord
            if ('.' in pattern) or pattern.isdigit():
                notes_in_chord = pattern.split('.')
                notes = []
                for current_note in notes_in_chord:
                    new_note = note.Note(int(current_note))
                    new_note.storedInstrument = instrument.Piano()
                    notes.append(new_note)
                new_chord = chord.Chord(notes)
                new_chord.offset = offset
                new_chord.duration = duration.Duration(dur)
                output_notes.append(new_chord)
            # pattern is a rest
            elif pattern is 'NULL':
              offset += TIMESTEP
            # pattern is a note
            else:
                new_note = note.Note(pattern)
                new_note.offset = offset
                new_note.storedInstrument = instrument.Piano()
                new_note.duration = duration.Duration(dur)
                output_notes.append(new_note)

            # increase offset each iteration so that notes do not stack
            offset += TIMESTEP

        midi_stream = stream.Stream(output_notes)

        output_file = MODEL_NAME + '.mid'
        print('output to ' + output_file)
        midi_stream.write('midi', fp=output_file)

g = Generator(MODEL_NAME + '_generator.hdf5')
#g = Generator("gan-transposed-nulls-variableLength-new-game-music5-e2000-s32-batch1800_generator.hdf5")
g.generate()