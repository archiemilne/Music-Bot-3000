import os
import mido
import json

def json_to_midi(input_folder, output_folder):
    for file in os.listdir(input_folder):
        if file.endswith(".json"):
            input_file = os.path.join(input_folder, file)
            output_file = os.path.join(output_folder, file.replace('.json', '.mid'))
            
            with open(input_file, 'r') as f:
                json_data = f.read()

            data = json.loads(json_data)

            midi = mido.MidiFile()
            for track_data in data:
                track = mido.MidiTrack()
                midi.tracks.append(track)
                for msg_data in track_data:
                    time, msg_type, msg_dict = msg_data
                    if msg_type == 'message':
                        msg = mido.Message.from_dict(msg_dict)
                    elif msg_type == 'meta':
                        msg = mido.MetaMessage.from_dict(msg_dict)
                    msg.time = time
                    track.append(msg)

            midi.save(output_file)

input_folder = '3json_in'
output_folder = '4midi_out'
os.makedirs(output_folder, exist_ok=True)
json_to_midi(input_folder, output_folder)
