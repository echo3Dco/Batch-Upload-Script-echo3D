"""
Python upload.py
Build a publishable script to batch upload models into echo3D
"""

import argparse
from enum import IntEnum
import requests
import csv
from pathlib import Path
import os
from pprint import pprint

FILE_PATH_ARGS_NAME = {'file_image', 'asset_file'}
UPLOAD_URL = 'https://api.echo3D.com/upload'

# Lists of supported file extensions for each hologram asset type
VIDEO_EXTENSION = {'mp4', 'mov'}
IMAGE_EXTENSION = {'jpg', 'jpeg', 'png', 'gif', 'tiff', 'bmp', 'svg'}
MODEL_EXTENSION = {'obj', 'gltf', 'glb', 'fbx', 'usdz', 'stl', 'blend', 'dae', 'sldprt', 'sldasm', 'step'}

class TargetType(IntEnum):
    IMAGE_TARGET = 0
    GEOLOCATION_TARGET = 1
    BRICK_TARGET = 2

class HologramType(IntEnum):
    VIDEO_HOLOGRAM = 0
    IMAGE_HOLOGRAM = 1
    MODEL_HOLOGRAM = 2

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('api_key', type=str,
                        help='Your Echo3D API key')
    parser.add_argument('security_key', type=str,
                        help='Your Echo3D security key. Only if enabled through the security page')
    parser.add_argument('email', type=str, 
                        help='Your user email')
    parser.add_argument('body_args', type=str,
                        help='A csv file containing all other arguments for POST body. Check out the example file template.csv for more details')

    args = parser.parse_args()
    data, files = build_body_args(args)

    if process_target_type(data, files) != 0:
        print('Above errors need to be resolved in order to continue the batch upload process')
        return -100

    if process_hologram_type(data, files) != 0:
        print('Above errors need to be resolved in order to continue the batch upload process')
        return -200
    
    print("===Body Form-Data Preview===")
    pprint(data)
    pprint(files)
    print("============================")

    r = post(data, files)
    print("Status code:", r.status_code)
    print("===API returned message below===")
    print(r.text)
    print("================================")

    return 0

"""
Initialize arguments to build form-data for POST body
"""
def build_body_args(args):
    data = {}
    files = {}
    data['key'] = args.api_key
    data['secKey'] = args.security_key
    data['email'] = args.email
    
    if not os.path.exists(Path(args.body_args)):
        print("[CSV FILE NOT FOUND] Invalid filepath for body_args which is '%s': No such file or directory" % (args.body_args))
        exit(-2)

    with open(args.body_args) as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            if len(row) != 2:
                print("[CSV FORMAT ERROR] The number of columns in one of your rows in %s is %d. The csv file must contain only two columns: one for argument name and the second for values." % (args.body_args, len(row)))
                exit(-3)

            if row[0] in FILE_PATH_ARGS_NAME:
                # Skip if the argument name key has no corresponding values
                if not row[1]:
                    continue

                try:
                    files[row[0]] = open(Path(row[1]), 'rb')
                except FileNotFoundError:
                    print("[FILE PATH ERROR] File argument '%s' contains an invalid filepath which is '%s': No such file or directory" % (row[0], row[1]))
                    exit(-4)
            else:
                # Skip if the argument name key has no corresponding values
                if not row[1]:
                    continue

                data[row[0]] = row[1]

    return data, files

"""
Process target type. 
Handles all target_type related errors. 
"""
def process_target_type(data, files):
    # Check if target_type are specified correctly.
    if 'target_type' not in data:
        print('[BODY ARGS ERROR] Missing target_type. Please check your csv file')
        return -10
    else:
        # Check the validity of hologram_type value
        # Also try to parse the input raw string value into integer
        try:
            data['target_type'] = int(data['target_type'])
            target_type = TargetType(data['target_type'])
        except ValueError:
            print('[TARGET TYPE ERROR] Invalid value for target_type. Please check upload documentation for a list of appropriate values!')
            return -11

    if target_type == TargetType.IMAGE_TARGET:
        if 'url_image' not in data and 'file_image' not in files:
            print("[IMAGE TARGET ERROR] Either url_image or file_image must be specified in your csv file")
            return -20
        elif 'url_image' in data and 'file_image' in files:
            print("[IMAGE TARGET ERROR] You cannot specify both url_image and file_image. You must only specify one of them in your csv file")
            return -21
        
    if target_type == TargetType.GEOLOCATION_TARGET:
        if not check_coordinates(data) and 'text_geolocation' not in data:
            print("[GEOLOCATION TARGET ERROR] Either text_geolocation or coordinate info (longitude and latitude) must be specified in your csv file. Hint: For coordinate info did you specify both longitude and latitude?")
            return -22
        elif check_coordinates(data) and 'text_geolocation' in data:
            print("[GEOLOCATION TARGET ERROR] You cannot specify both text_geolocation and coordinate info (longitude and latitude). You must only specify one of them in your csv file. Hint: For coordinate info did you specify both longitude and latitude?")
            return -23
        
        if check_coordinates(data):
            try:
                data['longitude'] = float(data['longitude'])
                data['latitude'] = float(data['latitude'])
            except ValueError:
                print("[GEOLOCATION TARGET ERROR] Longitude and latitude information must be in float")
                return -24
            
    return 0

"""
Automatically calculate the hologram type based on the extension of uploaded file.
Automatically assign filepath to respective keyword based on calculated hologram type.
Handles all hologram_type related errors. 
"""
def process_hologram_type(data, files):        
    if 'asset_file' in files and 'url_video' in data:
        print("[BODY ARGS ERROR] You cannot specify both asset_file and url_video. You must specify only one of them in your csv file")
        return -30
    
    if 'asset_file' not in files and 'url_video' not in data:
        print("[BODY ARGS ERROR] Missing asset_file or url_video argument. You need to specify one of them in your csv file")
        return -31
    
    if 'asset_file' in files:
        _, file_extension = os.path.splitext(files['asset_file'].name)
        file_extension = file_extension.replace('.', '')
        
        if not file_extension:
            print('[FILE EXTENSION ERROR] Missing file extension. Please check your file')
            return -40
        hologram_type = calculate_hologram_type(file_extension)
        if hologram_type == -1:
            print("[FILE EXTENSION ERROR] File extension %s is not supported" % (file_extension))
            return -41

        data['hologram_type'] = int(hologram_type)

        if hologram_type == HologramType.VIDEO_HOLOGRAM:
            files['file_video'] = files['asset_file']
            
        if hologram_type == HologramType.IMAGE_HOLOGRAM:
            files['file_image_hologram'] = files['asset_file']
            
        if hologram_type == HologramType.MODEL_HOLOGRAM:
            files['file_model'] = files['asset_file']
            data['type'] = 'upload'

        del files['asset_file']

    elif 'url_video' in data:
        hologram_type = HologramType.VIDEO_HOLOGRAM
        data['hologram_type'] = int(hologram_type)
        
    return 0

"""
Check if both longitude and latitude are specified for coordinate information
"""
def check_coordinates(data):
    return 'longitude' in data and 'latitude' in data

def calculate_hologram_type(file_extension):
    if file_extension in VIDEO_EXTENSION:
        return HologramType.VIDEO_HOLOGRAM
    elif file_extension in IMAGE_EXTENSION:
        return HologramType.IMAGE_HOLOGRAM
    elif file_extension in MODEL_EXTENSION:
        return HologramType.MODEL_HOLOGRAM
    else:
        return -1

"""
Invoke Echo3D API for POST request
"""
def post(data, files):
    return requests.post(UPLOAD_URL, data=data, files=files)

if __name__ == '__main__':
    main()
