import os
import mido
import json

def midi_to_json(input_folder, output_folder):
    for file in os.listdir(input_folder):
        if file.endswith(".mid") or file.endswith(".midi"):
            input_file = os.path.join(input_folder, file)
            output_file = os.path.join(output_folder, file.replace('.mid', '.json').replace('.midi', '.json'))
            
            midi = mido.MidiFile(input_file)

            data = []
            for track in midi.tracks:
                track_data = []
                for msg in track:
                    if not msg.is_meta:
                        msg_type = 'message'
                        msg_data = msg.dict()
                    else:
                        msg_type = 'meta'
                        msg_data = msg.dict()
                    track_data.append([msg.time, msg_type, msg_data])
                data.append(track_data)

            json_data = json.dumps(data)
            with open(output_file, 'w') as f:
                f.write(json_data)

input_folder = '1midi_in'
output_folder = '2json_out'
os.makedirs(output_folder, exist_ok=True)
midi_to_json(input_folder, output_folder)
