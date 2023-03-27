import os
os.environ["CUDA_VISIBLE_DEVICES"]="0" # use the first GPU device

import numpy as np
from music21 import converter, instrument, note, chord, stream
from keras.layers import LSTM, Dense, Activation, Dropout
from keras.models import Sequential
from keras.utils import np_utils
from keras.callbacks import ModelCheckpoint
import tensorflow as tf
tf.compat.v1.keras.backend.set_session(tf.compat.v1.Session())

# Constant defs
INPUT_FOLDER = 'midi_in'
OUTPUT_FOLDER = 'midi_out'
SEQUENCE_LENGTH = 200
EPOCHS = 100
BATCH_SIZE = 32
TEMPERATURE = 1.0

# Configure TensorFlow to use GPU
config = tf.compat.v1.ConfigProto()
config.gpu_options.allow_growth = True
tf.compat.v1.keras.backend.set_session(tf.compat.v1.Session(config=config))

# Parse MIDI files
def parse_midi_files(folder):
    notes = []
    for file in os.listdir(folder):
        if file.endswith('.mid'):
            print(f"Processing: {file}")
            try:
                midi = converter.parse(os.path.join(folder, file))
                notes_to_parse = None

                parts = instrument.partitionByInstrument(midi)
                if parts:
                    notes_to_parse = parts.parts[0].recurse()
                else:
                    notes_to_parse = midi.flat.notes

                for element in notes_to_parse:
                    if isinstance(element, note.Note):
                        notes.append(str(element.pitch))
                    elif isinstance(element, chord.Chord):
                        notes.append('.'.join(str(n) for n in element.normalOrder))
            except Exception as e:
                print(f"Error processing {file}: {e}")

    return notes

# Prepare the sequences
def prepare_sequences(notes, n_vocab):
    sequence_length = SEQUENCE_LENGTH
    pitchnames = sorted(set(item for item in notes))

    note_to_int = dict((note, number) for number, note in enumerate(pitchnames))
    network_input = []
    network_output = []

    for i in range(0, len(notes) - sequence_length, 1):
        sequence_in = notes[i:i + sequence_length]
        sequence_out = notes[i + sequence_length]
        network_input.append([note_to_int[char] for char in sequence_in])
        network_output.append(note_to_int[sequence_out])

    n_patterns = len(network_input)

    # Reshape the input and normalize
    network_input = np.reshape(network_input, (n_patterns, sequence_length, 1)) / float(n_vocab)
    network_output = np_utils.to_categorical(network_output)

    return network_input, network_output

# Create the LSTM model
def create_lstm_model(input_shape, n_unique_notes):
    model = Sequential()
    model.add(LSTM(512, input_shape=input_shape, return_sequences=True))
    model.add(Dropout(0.2))
    model.add(LSTM(512, return_sequences=True))
    model.add(Dropout(0.2))
    model.add(LSTM(512))
    model.add(Dropout(0.2))
    model.add(Dense(256))
    model.add(Activation('relu'))
    model.add(Dropout(0.2))
    model.add(Dense(n_unique_notes))
    model.add(Activation('softmax'))
    model.compile(loss='categorical_crossentropy', optimizer='adam')
    return model

# Generate the musical notes from the model
def generate_notes(model, network_input, pitchnames, n_notes, temperature=1.0):
    start = np.random.randint(0, len(network_input) - 1)
    int_to_note = dict((number, note) for number, note in enumerate(pitchnames))
    pattern = network_input[start]
    prediction_output = []

    for note_index in range(n_notes):
        prediction_input = np.reshape(pattern, (1, len(pattern), 1))
        prediction_input = prediction_input / float(len(pitchnames))
        prediction = model.predict(prediction_input, verbose=0)

        # Apply temperature
        prediction = np.log(prediction) / temperature
        exp_preds = np.exp(prediction)
        prediction = exp_preds / np.sum(exp_preds)

        # Sample from the predicted probabilities
        index = np.random.choice(range(len(prediction[0])), p=prediction[0])
        result = int_to_note[index]
        prediction_output.append(result)
        pattern = np.append(pattern, index)
        pattern = pattern[1:len(pattern)]

    return prediction_output

# Create the midi file from the output
def create_midi(prediction_output, output_folder, filename="output"):
    offset = 0
    output_notes = []

    for pattern in prediction_output:
        if ('.' in pattern) or pattern.isdigit():
            notes_in_chord = pattern.split('.')
            notes = []
            for current_note in notes_in_chord:
                new_note = note.Note(int(current_note))
                new_note.storedInstrument = instrument.Piano()
                notes.append(new_note)
            new_chord = chord.Chord(notes)
            new_chord.offset = offset
            output_notes.append(new_chord)
        else:
            new_note = note.Note(pattern)
            new_note.offset = offset
            new_note.storedInstrument = instrument.Piano()
            output_notes.append(new_note)

        offset += 0.5

    midi_stream = stream.Stream(output_notes)
    midi_stream.write('midi', fp=os.path.join(output_folder, f'{filename}.mid'))

def main():
    notes = parse_midi_files(INPUT_FOLDER)
    n_vocab = len(set(notes))
    network_input, network_output = prepare_sequences(notes, n_vocab)
    model = create_lstm_model(network_input.shape[1:], n_vocab)

    # Add the ModelCheckpoint callback to save the model weights every 10 epochs
    checkpoint_callback = ModelCheckpoint(
        filepath='weights/weights.{epoch:02d}.hdf5',
        period=10,
        save_weights_only=True,
    )

    model.fit(network_input, network_output, epochs=EPOCHS, batch_size=BATCH_SIZE, callbacks=[checkpoint_callback])
    pitchnames = sorted(set(item for item in notes))

    # Generate MIDI files for each saved set of weights
    for i in range(10, EPOCHS + 1, 10):
        model.load_weights(f'weights/weights.{i:02d}.hdf5')
        prediction_output = generate_notes(model, network_input, pitchnames, SEQUENCE_LENGTH, temperature=TEMPERATURE)
        create_midi(prediction_output, OUTPUT_FOLDER, f'output_epoch_{i}')

if __name__ == '__main__':
    main()