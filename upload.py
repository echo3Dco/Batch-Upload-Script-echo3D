"""
Python upload.py
Build a publishable script to batch upload models into echo3D
"""

import argparse
from enum import Enum
import requests
import csv
from pathlib import Path
import os
from pprint import pprint

FILE_PATH_ARGS_NAME = {'file_image', 'file_video', 'file_image_hologram', 'file_model', 'png_path'}
SUPPORTED_SOURCES = {'Sketchfab', 'Poly'}
UPLOAD_URL = 'https://api.echo3D.com/upload'

VIDEO_EXTENSION = {'mp4', 'mov'}
IMAGE_EXTENSION = {'jpg', 'jpeg', 'png', 'gif', 'tiff', 'bmp', 'svg'}
MODEL_EXTENSION = {'obj', 'gltf', 'glb', 'fbx', 'usdz', 'stl', 'blend', 'dae', 'sldprt', 'sldasm', 'step'}

class TargetType(Enum):
    IMAGE_TARGET = 0
    GEOLOCATION_TARGET = 1
    BRICK_TARGET = 2

class HologramType(Enum):
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
    print("===Body Form-Data Preview===")
    pprint(data)
    pprint(files)
    print("============================")

    if body_args_error_handle(data, files) != 0:
        print('Above errors need to be resolved in order to continue the batch upload process')
        return -100

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
                    print("[FILE PATH ERROR] File argument key '%s' in '%s' contains an invalid filepath which is '%s': No such file or directory" % (row[0], args.body_args, row[1]))
                    exit(-4)
            else:
                # Skip if the argument name key has no corresponding values
                if not row[1]:
                    continue

                data[row[0]] = row[1]

    return data, files

"""
Error handling for missing arguments
"""
def body_args_error_handle(data, files):
    # Check if target_type are specified correctly.
    if 'target_type' not in data:
        print('[BODY ARGS ERROR] Missing target type. Please check your csv file')
        return -50
    else:
        # Check the validity of hologram_type value
        try:
            target_type = TargetType(int(data['target_type']))
        except ValueError:
            print('[TARGET TYPE ERROR] Invalid value for target_type. Please check upload documentation for appropriate values!')
            return -51

    # Check if hologram_type are specified correctly.
    if 'hologram_type' not in data:
        print('[BODY ARGS ERROR] Missing hologram type. Please check your csv file')
        return -52
    else:
        # Check the validity of hologram_type value
        try:
            hologram_type = HologramType(int(data['hologram_type']))
        except ValueError:
            print('[HOLOGRAM TYPE ERROR] Invalid value for hologram_type. Please check upload documentation for appropriate values!')
            return -53

    if target_type == TargetType.IMAGE_TARGET:
        if 'url_image' not in data and 'file_image' not in files:
            print("[IMAGE TARGET ERROR] Either url_image or file_image must be specified in your csv file")
            return -10
        elif 'url_image' in data and 'file_image' in files:
            print("[IMAGE TARGET ERROR] You cannot specify both url_image and file_image. You must only specify one of them in your csv file")
            return -11
        
    if target_type == TargetType.GEOLOCATION_TARGET:
        if not check_coordinates(data) and 'text_geolocation' not in data:
            print("[GEOLOCATION TARGET ERROR] Either text_geolocation or coordinate info (longitude and latitude) must be specified in your csv file. Hint: For coordinate info did you specify both longitude and latitude?")
            return -12
        elif check_coordinates(data) and 'text_geolocation' in data:
            print("[GEOLOCATION TARGET ERROR] You cannot specify both text_geolocation and coordinate info (longitude and latitude). You must only specify one of them in your csv file. Hint: For coordinate info did you specify both longitude and latitude?")
            return -13
        
        if check_coordinates(data):
            try:
                data['longitude'] = float(data['longitude'])
                data['latitude'] = float(data['latitude'])
            except ValueError:
                print("[GEOLOCATION TARGET ERROR] Longitude and latitude information must be float")
                return -14

    if hologram_type == HologramType.VIDEO_HOLOGRAM:
        if 'url_video' not in data and 'file_video' not in files:
            print("[VIDEO HOLOGRAM ERROR] Either url_video or file_video must be specified in your csv file")
            return -20
        if 'url_video' in data and 'file_video' in files:
            print("[VIDEO HOLOGRAM ERROR] You cannot specify both url_video and file_video. You must only specify one of them in your csv file")
            return -21
        
    if hologram_type == HologramType.IMAGE_HOLOGRAM:
        if 'file_image_hologram' not in files:
            print("[IMAGE HOLOGRAM ERROR] You must specify file_image_hologram in your csv file")
            return -22
        
    if hologram_type == HologramType.MODEL_HOLOGRAM:
        if 'type' not in data:
            print("[MODEL HOLOGRAM ERROR] You must specify 'type' argument in your csv file")
            return -23
        if data['type'] not in {'upload', 'search'}:
            print("[MODEL HOLOGRAM ERROR] 'type' argument only accepts 'upload' or 'search' values")
            return -24
        if data['type'] == 'upload' and 'file_model' not in files:
            print("[MODEL HOLOGRAM ERROR] You must specify file_model argument as the filepath of your model if the upload option is chosen")
            return -25
        if data['type'] == 'search' and ('source' not in data or 'name' not in data):
            print("[MODEL HOLOGRAM ERROR] You must specify both the source argument and name argument in your csv file if the search option is chosen")
            return -26
        if data['type'] == 'search' and data['source'] not in SUPPORTED_SOURCES:
            print("[MODEL HOLOGRAM ERROR] Specified source %s is not supported. Currently only Sketchfab is supported." % (data['source']))
            return -27
        # Google Poly was shut down and therefore it is impossible to retrieve any models from it. 
        if data['type'] == 'search' and data['source'] == 'Poly':
            print("[MODEL HOLOGRAM ERROR] Google Poly is no longer supported as the server was shut down on June 30, 2021")
            return -28
        if data['type'] == 'search' and data['source'] == 'Sketchfab' and 'url' not in data:
            print("[MODEL HOLOGRAM ERROR] You must specify the url argument in your csv file, which is the Sketchfab API URL redirecting to the model. Should be in the form of https://api.sketchfab.com/v3/models/<ID>/download")
            return -29
        
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
        print('[FILE EXTENSION ERROR] File extension %s is not supported.' % (file_extension))
        return -1
    a
"""
Invoke Echo3D API for POST request
"""
def post(data, files):
    return requests.post(UPLOAD_URL, data=data, files=files)

if __name__ == '__main__':
    main()
