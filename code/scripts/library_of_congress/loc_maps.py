import argparse
import datetime as dt
import logging
import re
import requests
import sys
import yaml
from pathlib import Path


DESCRIPTION = """
    This script retrieves a single volume of map images from the Library of Congress. The script
    requires that two command line arguments be provided:

    1. a < key > string value that matches a map key in the companion < loc_maps_config.yml > file.
    2. an < output > filepath string value for local storage of the retrieved images.

    The 'key' arg is used to filter on the relevant map data contained in the loaded YAML file.

    Once configured, the script retrieves the target images, renames the downloaded files,
    stores them locally in the < output > location, and logs the process both the the screen and
    a log file.

    The LOC also makes available large JPEG 2000 and TIFF images.
    """


def configure_logger(output_path, filename_segments, start_date_time):
    """Returns a logger object with stream and file handlers.

    Parameters:
        output_path (str): relative directory path were file is to be located
        filename_segments (list): filename segments
        start_date_time (datetime): start datetime.

    Returns:
        Path: path object (absolute path)
    """

    # Set logging format and default level
    logging.basicConfig(
        format='%(levelname)s: %(message)s',
        level=logging.DEBUG
    )

    logger = logging.getLogger()
    # logger.setLevel(logging.DEBUG)

    # Create filename and path
    filename = create_filename(filename_segments, extension='.log')
    filepath = create_filepath(output_path, filename)

    # Add file and stream handlers
    logger.addHandler(logging.FileHandler(filepath))
    logger.addHandler(logging.StreamHandler(sys.stdout))

    return logger


def create_filename(name_segments, part=None, num=None, extension='.jpg'):
    """Returns a Path object comprising a filename built up from a list
    of name segments.

    Parameters:
        name_segments (list): file name segments
        part (str): optional LOC image designator (e.g., index)
        num (str): image number (typically zfilled)
        extension (str): file extension; defaults to .jpg

    Returns:
        Path: path object
    """

    segments = name_segments['name'].copy() # shallow copy

    # Add additional segments
    if name_segments['year']:
        segments.append(str(name_segments['year']))
    if name_segments['vol']:
       segments.append(f"vol_{name_segments['vol']}")

    if extension == '.log':
        return Path('-'.join(segments)).with_suffix(extension)

    # Continue adding segments for non-log files
    if name_segments['vol']:
        segments.append(f"vol_{name_segments['vol']}")
    if part:
        segments.append(part)
    if num:
        if len(num) < 4: # pad
            num = num.zfill(4)
        segments.append(num)

    return Path('-'.join(segments)).with_suffix(extension)


def create_filepath(output_path, filename):
    """Return local filepath for image and log files.

    Parameters:
        output_path (str): relative directory path were file is to be located
        filename (str): name of file including extension

    Returns:
        Path: path object (absolute path)
    """

    return Path(Path.cwd(), output_path, filename)


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
        help="Required YAML map key"
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

    map_key = cli_args.key
    output_path = cli_args.out

    # load YAML config
    filepath = 'loc_maps_config.yml'
    config = read_yaml_file(filepath)

    # YAML config values
    host = config['host']
    map_config = config['maps'][map_key] # filter on CLI arg
    filename_segments = map_config['filename_segments']

    # Configure and start logger
    start_date_time = dt.datetime.now()
    logger = configure_logger(output_path, filename_segments, start_date_time)
    logger.info(f"Start run: {start_date_time.isoformat()}")
    # logger.info(f"Start run: {now.strftime('%Y-%m-%d-%H:%M:%S')}") # alternative

    # Retrieve files
    for path in map_config['paths']:

        prefix = path['prefix']
        part = path['part'] # part of work (e.g., index)
        default_path = path['default_path']

        # Compile regex (used in inner loop)
        regex = re.compile(path['regex']) # assigned as a raw string (e.g., r"_1925-[0-9]*")

        # Pad image number
        zfill_width = path['index']['zfill_width']

        for i in range(path['index']['start'], path['index']['stop'], 1):

            # Add zfill if required
            num = str(i)
            if zfill_width > 0:
                num = num.zfill(zfill_width)

            # LOC resource URL (regex replacement)
            repl = f"{prefix}{num}" # repl = replace
            resource_url = f"{host}{regex.sub(repl, default_path)}"

            # Retrieve binary content
            # Images are small in size so no need to stream in chunks
            response = requests.get(resource_url)

            # Create filename and path
            filename = create_filename(filename_segments, part, num)
            filepath = create_filepath(output_path, filename)

            # Write binary content (mode=wb)
            write_file(filepath, response.content, 'wb')

            # Log new file name
            logger.info(f"Renamed file to {filepath.name}")


    # End run
    logger.info(f"End run: {dt.datetime.now().isoformat()}")
    # logger.info(f"End run: {end_date_time.strftime('%Y-%m-%d-%H:%M:%S')}") # alternative


if __name__ == '__main__':
    main(sys.argv[1:]) # ignore the first element (program name)
