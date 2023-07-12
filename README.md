# Echo3D 3D Models Batch Upload Script

## About this repository

This repository contains a publishable python script to batch upload models into echo3D. It feeds in arguments from parsing and csv file, and automatically make a POST request to Echo3D upload API.

## Requirements

* `Python 3.8.16`
* `requests`

## Instructions for package installation

1. Download and install Python 3.8.16 from https://www.python.org/downloads/release/python-3816/. By default, pip (a Python package installation tool) should also come with it.

2. Run the following commands:
   
   `pip install requests`
   
   Above commands should install `requests` to your Python environment. After that, you should be able to run the script. 

## Echo3D API Instructions

1. Register for a FREE account at echo3D.
3. Get your API key.
4. Get your security key.

## Running Instructions

1. Install all required packages and follow the Echo3D API instructions as described above.

2. Download the `upload.py` script and the `template.csv` file to your working directory.

3. Open a terminal from your working directory. Make sure that Python 3.8.16 is properly installed by running the command `python --version`. Also make sure that `requests` is installed. 

4. Run the command as follows:
   
   `python upload.py [API_KEY] [SECURITY_KEY] [EMAIL] [TARGET_TYPE] [HOLOGRAM_TYPE] [BODY_ARGS]`

   where
   
   * `[API_KEY]` is your Echo3D API key
   * `[SECURITY_KEY]` is your security key
   * `[EMAIL]` is the registered email of your echo3D account
   * `[TARGET_TYPE]` is an integer specifying desired target type. Check out https://docs.echo3d.com/upload#target-type for detailed documentation.
   * `[HOLOGRAM_TYPE]` is an integer specifying desired hologram asset type. Check out https://docs.echo3d.com/upload#asset-type for detailed documentation.
   * `[BODY_ARGS]` is the path to your csv file that contains all other arguments needed for making a POST request to echo3D API. Check out the `template.csv`. The raw `csv` file must be separated by comma and contain exactly 2 columns similar to a key-value pair. 

5. If all arguments are filled correctly, the API will return status code of 200 and the entry json information of uploaded model. A code of 500 is an internal server exception, but it is most likely that your inputs may be incorrect. 

### Error handling

This script can handle following errors:
 
 * Missing required arguments
 * Invalid file path for `csv` or model files (File not found error)
 * Validity of values for longitude and latitude arguments. (Must be floating point)
 * Validity of target and hologram asset type. 

If above errors are detected, the script will print the corresponding error message and stop the uploading process. For other errors that are not listed above, the script will either print out a status code of 400 or 500 from the echo3D API server, or raise a python exception. 

## About `template.csv`

`template.csv` is the file that contains additional arguments needed to upload assets with a POST query. For example, if you choose to upload an image hologram (by specifying integer `1` in the hologram asset type), you will need to also specify the `file_image_hologram` argument. In this case, you need to specify such argument in the `template.csv` file. 

To check out the required arguments for your specified target and hologram asset type, please go to https://docs.echo3d.com/upload. 

By default, `template.csv` contains all additional arguments as keys. If an argument is not needed under your desired target or hologram asset type, just leave the value blank. Only fill out the values of needed arguments.  

For arguments that require a file upload, you need to specify the path to your file. 

## Example run

Here is a upload API examples using this script:

1. Uploading a model asset on a surface target from local storage:
    * type is `upload` and file_model includes a file
    * hologram_type is 2
    * target_type is 2

    `python upload.py abc-defg-123 abc123456789 yourname@gmail.com 2 2 template.csv`

    where `template.csv` is as follows:

    |  |  |
    | ----------- | ----------- |
    | url_image      |        |
    | file_image   |         |
    | text_geolocation   |         |
    | longitude   |        |
    | latitude   |        |
    | url_video   |        |
    | file_video   |         |
    | file_image_hologram  |         |
    | type   | upload       |
    | file_model   | path/to/your/model/file        |
    | source   |        |
    | url   |       |
    | name   |        |
    | file_cvs   |        |
    | edit_type |        |
    | entryId   |        |

    As shown above, arguments that are not needed are left blank. Only the required arguments are filled. 




