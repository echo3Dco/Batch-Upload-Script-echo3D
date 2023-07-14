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
import json

VALID_ARGUMENTS = {'longitude', 'file_image', 'asset_file', 'file_cvs', 'url_image', 'target_type', 'latitude',
                   'text_geolocation', 'url_video'}
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
                        help='Filepath to your csv file containing all other arguments for POST body. Check out the '
                             'template.csv as an example')

    args = parser.parse_args()
    file_list = build_body_form_data(args)
    if not file_list:
        print("[WARNING] Your csv file is empty! No files are uploaded!")
        return 0

    print("===Body Form-Data Preview===")
    pprint(file_list)
    print("============================")

    post(file_list)
    print("All upload queries have been processed by Echo3D API. An out.txt file storing API returned status code and "
          "results is generated")

    return 0


# Build form-data for POST query
def build_body_form_data(args):
    if not os.path.exists(Path(args.body_args)):
        print("[CSV FILE NOT FOUND] Invalid filepath for body_args which is '%s': No such file or directory" %
              args.body_args)
        exit(-2)

    file_list = []
    with open(args.body_args) as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        header_list = next(reader)

        # Check if all argument fields in csv header are valid. (Not empty and is a valid argument name)
        for argument_field in header_list:
            if not argument_field:
                print(
                    "[CSV FORMAT ERROR] One of your argument fields in csv header is empty. Please check your csv file")
                exit(-3)

            if argument_field not in VALID_ARGUMENTS:
                print(
                    "[CSV FORMAT ERROR] '%s' is not a valid argument name in csv header. Valid argument names are %s" %
                    (argument_field, VALID_ARGUMENTS))
                exit(-4)

        # Check if there are duplicate argument fields in csv header. 
        header_set = set(header_list)
        if len(header_set) != len(header_list):
            print("[CSV FORMAT ERROR] Duplicate argument fields in csv header exist. Please check your csv file")
            exit(-5)

        # Begin reading the data
        csv_line = 2
        for row in reader:
            data = {'key': args.api_key, 'secKey': args.security_key, 'email': args.email}
            files = {}

            if len(row) != len(header_list):
                print(
                    "[CSV FORMAT ERROR] A row has different number of columns from header. Please check your csv file")
                print("Above error was detected in line %d of your csv file. You need to resolve it before continuing "
                      "the batch upload process" % csv_line)
                exit(-6)

            for i in range(len(row)):
                if header_list[i] in FILE_PATH_ARGS_NAME:
                    # Skip if the argument name key has no corresponding values
                    if not row[i]:
                        continue

                    try:
                        files[header_list[i]] = open(Path(row[i]), 'rb')
                    except FileNotFoundError:
                        print(
                            "[FILE PATH ERROR] File argument '%s' contains an invalid filepath which is '%s': No such "
                            "file or directory" % (header_list[i], row[i]))
                        print(
                            "Above error was detected in line %d of your csv file. You need to resolve it before "
                            "continuing the batch upload process" % csv_line)
                        exit(-7)

                else:
                    # Skip if the argument name key has no corresponding values
                    if not row[i]:
                        continue

                    data[header_list[i]] = row[i]

            if process_target_type(data, files) != 0 or process_hologram_type(data, files) != 0:
                print("Above error was detected in line %d of your csv file. You need to resolve it before continuing "
                      "the batch upload process" % csv_line)
                exit(-8)

            file_list.append({'data': data, 'files': files})
            csv_line += 1

    return file_list


# Process target type.
# Handles all target_type related errors.
def process_target_type(data, files):
    # Check if target_type are specified correctly.
    if 'target_type' not in data:
        print("[BODY ARGS ERROR] Missing target_type. Please check your csv file")
        return -10
    else:
        # Check the validity of hologram_type value
        # Also try to parse the input raw string value into integer
        try:
            data['target_type'] = int(data['target_type'])
            target_type = TargetType(data['target_type'])
        except ValueError:
            print(
                "[TARGET TYPE ERROR] Invalid value for target_type. Please check upload documentation for a list of "
                "appropriate values!")
            return -11

    if target_type == TargetType.IMAGE_TARGET:
        if 'url_image' not in data and 'file_image' not in files:
            print("[IMAGE TARGET ERROR] Either url_image or file_image must be specified in your csv file")
            return -20
        elif 'url_image' in data and 'file_image' in files:
            print(
                "[IMAGE TARGET ERROR] You cannot specify both url_image and file_image. You must only specify one of "
                "them in your csv file")
            return -21

    if target_type == TargetType.GEOLOCATION_TARGET:
        if not check_coordinates(data) and 'text_geolocation' not in data:
            print(
                "[GEOLOCATION TARGET ERROR] Either text_geolocation or coordinate info (longitude and latitude) must "
                "be specified in your csv file. For coordinate info you need to specify both longitude and "
                "latitude")
            return -22
        elif check_coordinates(data) and 'text_geolocation' in data:
            print(
                "[GEOLOCATION TARGET ERROR] You cannot specify both text_geolocation and coordinate info (longitude "
                "and latitude). You must only specify one of them in your csv file. For coordinate info you "
                "need to specify both longitude and latitude")
            return -23

        if check_coordinates(data):
            try:
                data['longitude'] = float(data['longitude'])
                data['latitude'] = float(data['latitude'])
            except ValueError:
                print("[GEOLOCATION TARGET ERROR] Longitude and latitude information must be in float")
                return -24

    return 0


# Automatically calculate the hologram type based on the extension of uploaded file.
# Automatically assign filepath to respective keyword based on calculated hologram type.
# Handles all hologram_type related errors.
def process_hologram_type(data, files):
    if 'asset_file' in files and 'url_video' in data:
        print(
            "[BODY ARGS ERROR] You cannot specify both asset_file and url_video. You must specify only one of them in "
            "your csv file")
        return -30

    if 'asset_file' not in files and 'url_video' not in data:
        print(
            "[BODY ARGS ERROR] Missing asset_file or url_video. You must specify one of them in your csv file")
        return -31

    if 'asset_file' in files:
        _, file_extension = os.path.splitext(files['asset_file'].name)
        file_extension = file_extension.replace('.', '')

        if not file_extension:
            print("[FILE EXTENSION ERROR] Missing file extension. Please check your file")
            return -40

        hologram_type = calculate_hologram_type(file_extension)
        if hologram_type == -1:
            print("[FILE EXTENSION ERROR] File extension '%s' is not supported" % file_extension)
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


# Check if both longitude and latitude are specified for coordinate information
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


# Invoke Echo3D API for POST request
def post(file_list):
    results = []
    for form_data in file_list:
        if form_data['files'] == {}:
            r = requests.post(UPLOAD_URL, data=form_data['data'])
        else:
            r = requests.post(UPLOAD_URL, data=form_data['data'], files=form_data['files'])

        result = {'status_code': r.status_code, 'response_text': r.text}
        results.append(result)

    json_dict = json.dumps(results)
    with open("out.json", "w") as outfile:
        outfile.write(json_dict)


if __name__ == '__main__':
    main()
