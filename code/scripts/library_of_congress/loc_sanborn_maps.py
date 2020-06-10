import argparse
import datetime as dt
import logging
import re
import requests
import sys
import yaml


DESCRIPTION = """
    This script retrieves a single volume of Sanborn Fire Insurance map images from the Library
    of Congress for a given municipality and year. The script requires that two command line
    arguments be provided:

    1. a < key > string value that matches a municipality key in the companion
        < loc_sanborn_params.yml > file
    2. an < output > filepath string value for local storage of the retrieved images.

    The 'key' arg is used to filter on relevant municipality data contained in the loaded YAML file.

    Once configured, the script retrieves the target images, renames the downloaded files,
    stores them locally in the < output > location, logs the process both the the screen and
    a log file.

    The LOC also makes available large JPEG 2000 and TIFF images.
    """

# TODO - use yaml service_path value


def configure_logger(municipality, start_date_time, output_path):

    # Set logging format and default level
    logging.basicConfig(
        format='%(levelname)s: %(message)s',
        level=logging.DEBUG
    )

    logger = logging.getLogger()
    # logger.setLevel(logging.DEBUG)

    # Log file
    filepath = f"{output_path}/Sanborn-LOC"
    filepath += f"-{municipality['name']}-{municipality['state']}-{municipality['year']}"
    if municipality['vol']:
        filepath += f"-vol_{municipality['vol']}"
    filepath += '.log'

    # Add file and stream handlers
    logger.addHandler(logging.FileHandler(filepath))
    logger.addHandler(logging.StreamHandler(sys.stdout))

    return logger


def create_filename(municipality, image_id, part=None):
    """Return local image filename.

    Parameters:
        municipality (dict): contains name, state, year, and file extension.
        image_num (str): map image identifier

    Returns:
        str: formatted filename
    """

    filename = 'Sanborn-LOC'
    filename += f"-{municipality['name']}-{municipality['state']}-{municipality['year']}"
    if municipality['vol']:
        filename += f"-vol_{municipality['vol']}"
    if part:
        filename += f"-{part}"
    if len(image_id) < 4:
        image_id = image_id.zfill(4)
    filename += f"-{image_id}.{municipality['extension']}"

    return filename


def create_parser(description):
    """Return a custom argument parser.

    Parameters:
       None

    Returns:
        parser (ArgumentParser): parser object
    """

    parser = argparse.ArgumentParser(description)

    parser.add_argument(
        '-k',
        '--key',
        type=str,
        required=True,
        help="Required YAML municipality key"
        )

    parser.add_argument(
        '-o',
        '--out',
        type=str,
        required=True,
        help="Output directory"
	)

    return parser


def read_yaml_file(filepath):
    """Read a YAML (Yet Another Markup Language) file given a valid filepath.

    Parameters:
        filepath (str): absolute or relative path to target file

    Returns:
        obj: typically a list or dictionary representation of the file object
    """

    with open(filepath, 'r') as file_object:
        data = yaml.load(file_object, Loader=yaml.FullLoader)

        return data


def write_file(filepath, data, mode='w'):
    """Writes content to a target file. Override the optional write mode value
    if binary content <class 'bytes'> is to be written to file (i.e., mode='wb')
    or an append operation is intended on an existing file (i.e., mode='a' or 'ab').

    Parameters:
        filepath (str): absolute or relative path to target file
        data (obj): data to be written to the target file
        mode (str): write operation mode

    Returns:
       None
    """

    with open(filepath, mode) as file_object:
        file_object.write(data)


def main(args):
    """Entry point. Orchestrates the workflow.

    Parameters:
        args (list): command line arguments

    Returns:
        None
    """

    # Parse CLI args
    cli_args = create_parser(DESCRIPTION).parse_args(args)

    municipality_key = cli_args.key
    output_path = cli_args.out

    # load YAML config
    filepath = 'loc_sanborn_params.yml'
    config = read_yaml_file(filepath)

    # YAML config values
    host = config['host']
    municipality = config['municipalities'][municipality_key] # filter on CLI arg

    # Start time
    start_date_time = dt.datetime.now()

    # Configure logger
    logger = configure_logger(municipality, start_date_time, output_path)

    # Start run
    logger.info(f"Start run: {start_date_time.isoformat()}")
    # logger.info(f"Start run: {now.strftime('%Y-%m-%d-%H:%M:%S')}") # alternative

    # Retrieve files
    for path in municipality['paths']:

        prefix = path['prefix']
        part = path['part'] # part of work (e.g., index)
        pad = path['pad_num']
        default_path = path['default_path']

        # Compile regex (used in inner loop)
        regex = re.compile(path['regex']) # assigned as a raw string (e.g., r"_1925-[0-9]*")

        for i in range(path['index_start'], path['index_stop'], 1):

            # Add zfill if required
            num = str(i)
            if pad:
                num = num.zfill(4)

            # LOC resource URL (regex replacement)
            repl = f"{prefix}{num}" # repl = replace
            resource_url = f"{host}{regex.sub(repl, default_path)}"

            # Retrieve binary content (images are small in size so no need to stream in chunks)
            response = requests.get(resource_url)

            # Write binary content (mode=wb)
            new_filename = create_filename(municipality, num, part)

            write_file(f"{output_path}/{new_filename}", response.content, 'wb')

            # Log new file name
            logger.info(f"Renamed file to {new_filename}")


    # End run
    logger.info(f"End run: {dt.datetime.now().isoformat()}")
    # logger.info(f"End run: {end_date_time.strftime('%Y-%m-%d-%H:%M:%S')}") # alternative


if __name__ == '__main__':
    main(sys.argv[1:]) # ignore the first element (program name)
