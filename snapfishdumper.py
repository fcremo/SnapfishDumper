#!/usr/bin/python
# coding=utf-8
__author__ = 'https://github.com/fcremo'

import requests
import requests.utils
import json
import argparse
import getpass
import os
import re
import multiprocessing
import logging
import signal
import sys

MIN_PROCESSES = 1
MAX_PROCESSES = 10
DEFAULT_PROCESSES = 5
DEFAULT_VERBOSITY = 2
DEFAULT_MODE = 'all'
DEFAULT_POD = 3
MIN_POD = 1
MAX_POD = 5
MIN_VERBOSITY = 1
MAX_VERBOSITY = 5
PROTO = "https://"
HOST = "www.snapfish.com"
PROTO_HOST = PROTO + HOST


def list_work(queue):
    """ Use a queue to distribute the jobs to the subprocesses """
    for i in range(0, queue.qsize()):
        yield queue.get()


def save_picture((session, url, path)):
    with open(path, 'wb') as handle:
        response = session.get(url, stream=True)

        if not response.ok:
            logging.warning("Error downloading" + url)

        for block in response.iter_content(4096):
            if not block:
                break
            handle.write(block)
    return


if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Snapfish dumper.',
                                     epilog='Example:\n'
                                            './snapfishdumper.py --dir albums --save pictures mail@provider.com\n\n'
                                            'This software is released under GNU GPLv2 license.',
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('username', metavar='username',
                        help='Snapfish login username/email')
    parser.add_argument('-p', '--password', metavar='password',
                        help='Snapfish account password. If omitted the password will be asked from stdin')
    parser.add_argument('-d', '--dir', metavar='download_dir', default=os.getcwd(),
                        help='Where to save the albums.'
                             'Default: current directory.')
    parser.add_argument('-c', '--concurrent', default=DEFAULT_PROCESSES,
                        help='Sets the max. number of concurrent downloads (%i-%i).'
                             'Default: %i' %
                             (MIN_PROCESSES, MAX_PROCESSES, DEFAULT_PROCESSES))
    parser.add_argument('-v', '--verbosity', choices=range(MIN_VERBOSITY, MAX_VERBOSITY+1), default=DEFAULT_VERBOSITY,
                        help='Sets the verbosity threshold (%i-%i, lower logs more).'
                             'Default: %i' % (MIN_VERBOSITY, MAX_VERBOSITY, DEFAULT_VERBOSITY,))
    parser.add_argument('-s', '--save', choices=['all', 'pictures', 'metadata'], dest='save', default=DEFAULT_MODE,
                        help='Download everything, just pictures or just json metadata.'
                             'Default: %s' % (DEFAULT_MODE,))
    parser.add_argument('--pod', choices=range(MIN_POD, MAX_POD+1), type=int, default=DEFAULT_POD,
                        help='Set the "pod" (server) that contains the user data. '
                             'It should match the number that you see in the url '
                             'after you log in on snapfish, eg. www3.snapfish.com => pod number 3.'
                             'Default: %i (just because it works for me)' % (DEFAULT_POD,))

    args = parser.parse_args()

    verbosity = args.verbosity
    if verbosity == 1:
        log_level = logging.DEBUG
    elif verbosity == 2:
        log_level = logging.INFO
    elif verbosity == 3:
        log_level = logging.WARNING
    elif verbosity == 4:
        log_level = logging.ERROR
    elif verbosity == 5:
        log_level = logging.CRITICAL
    logging.basicConfig(level=logging.ERROR)
    logger = logging.getLogger('snapfishdumper')
    logger.setLevel(log_level)

    logger.info('Starting snapfish dumper')

    username = args.username

    if args.password is None:
        password = getpass.getpass("Snapfish account password: ")
    else:
        password = args.password

    if MIN_PROCESSES <= int(args.concurrent) <= MAX_PROCESSES:
        processes = int(args.concurrent)
    else:
        print("Choose a number of concurrent downloads between %i and %i!" % (MIN_PROCESSES, MAX_PROCESSES))
        exit()

    if args.dir.startswith('/'):
        save_dir = args.dir
    else:
        save_dir = os.getcwd() + '/' + args.dir
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)
    else:
        logger.warning('The destination directory already exists')

    if args.save == 'all':
        logger.info('Saving everything')
        save_metadata = True
        save_pictures = True
    elif args.save == 'metadata':
        logger.info('Saving only metadata')
        save_metadata = True
        save_pictures = False
    else:
        logger.info('Saving only the pictures')
        save_metadata = False
        save_pictures = True

    podnum = args.pod
    PODHOST = "www" + str(podnum) + ".snapfish.com"
    PROTO_PODHOST = PROTO + PODHOST

    logger.debug('Performing authentication')
    session = requests.session()
    headers = {"Origin": PROTO_HOST,
               "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/41.0.2272.76 Safari/537.36"}
    session.headers.update(headers)

    # Perform authentication requests
    auth_url = "/snapfish/loginsubmit/fromTS=true/module=true/" \
               "topWindowHost=www.snapfish.com/istws=true/pns/snapfish/welcome"
    auth_data = {"avoidDomainValidation": "true",
                 "emailaddress": username,
                 "password": password,
                 "log in.x": 10,
                 "log in.y": 15}
    auth_header = {"Referer": PROTO_HOST + "/snapfish/login/fromTS=true/module=true/"
                                           "topWindowHost=www.snapfish.com/istws=true//pns/"}
    auth_request = session.post(PROTO_HOST + auth_url, data=auth_data, headers=auth_header)

    auth_url_2 = "/snapfish/loginsubmit/fromTS=true/module=true/" \
                 "topWindowHost=www.snapfish.com/istws=true/pns/snapfish/welcome"
    auth_data_2 = {"retuser": "FALSE",
                   "avoidDomainValidation": "true",
                   "session_COBRAND_NAME": "snapfish",
                   "cobrandOid": 1000,
                   "COBRAND_NAME": "snapfish",
                   "session_siteentry": "FDR",
                   "session_retuser": "FALSE",
                   "emailaddress": username,
                   "siteentry": "FDR",
                   "log in.y": 10,
                   "log in.x": 41,
                   "password": password,
                   "session_cobrandOid": 1000}
    auth_header_2 = {"Referer": PROTO_HOST + "/snapfish/loginsubmit/fromTS=true/module=true/"
                                             "topWindowHost=www.snapfish.com/istws=true/pns/snapfish/welcome"}
    auth_request_2 = session.post(PROTO_PODHOST + auth_url_2, data=auth_data_2, headers=auth_header_2)

    if '"loggedIn":true' not in auth_request_2.text:
        logger.critical('Cannot login. Please check your credentials and try to use a different pod.')
        exit()
    # TODO: use the appropriate pod (server) for the logged user

    # Get the list of the owned albums
    album_list_url = "/snapfish/fe/resources/{acct.albumListResourceUri}?accessLevel=owned"
    album_list_request = session.get(PROTO_PODHOST + album_list_url)
    album_list_json = album_list_request.text
    albums = json.loads(album_list_json)['album']

    if save_metadata:
        with open(save_dir + '/albums.json', 'w') as metadata_file:
            metadata_file.write(album_list_json.encode('utf8'))

    logger.info('Got %i albums' % (len(albums),))

    # Instantiate a pool of processes and a signal handler for CTRL+C termination
    # TODO: terminate the program instantly and consistently
    pool = multiprocessing.Pool(processes=processes)

    def signal_handler(signal, frame):
        logger.error('CTRL+C pressed. Terminating...')
        pool.close()
        pool.terminate()
        pool.join()
        sys.exit(1)
    signal.signal(signal.SIGINT, signal_handler)

    for album_number, album in enumerate(albums):

        album_details_params = {"getAlbumTags": "true",
                                "getPicOids": "true",
                                "sortOrder": "default",
                                "fromIndex": "0",
                                "itemCount": "1000"}
        album_details_request = session.get(PROTO_PODHOST + "/snapfish/fe/resources/beapi/website/snapfish_us/acct/" +
                                            str(album["ownerAcctOid"]) + "/album/" + str(album["albumOid"]) +
                                            "/granterId/" + str(album["ownerAcctOid"]) + "/albumDetail",
                                            params=album_details_params)
        album_details_json = album_details_request.text
        album_details = json.loads(album_details_json)
        logger.info("Downloading album %i of %i: %s", album_number + 1,
                    len(albums), album_details['albumInfo']['albumName'])
        album_pictures = album_details['userAssets']['userAsset']

        album_dir_name = re.sub('[^\\w_\\-\\. ]', '', album_details['albumInfo']['albumName'])
        try:
            os.mkdir(save_dir + '/' + album_dir_name)
        except OSError:
            # TODO: decide what to do in case the album dir already exists:
            # Are there two albums which generate the same dir name, the album was already downloaded or what?
            # A possibility is to use the albumOid do distinguish them
            # album_dir_name = album_dir_name + '_' + str(album_details['albumInfo']['albumOid'])
            # os.mkdir(save_dir + '/' + album_dir_name)
            # For now we just download the pictures that don't already exist
            pass

        if save_metadata:
            with open(save_dir + '/' + album_dir_name + '/album.json', 'w') as metadata_file:
                metadata_file.write(album_details_json.encode('utf8'))

        pictures_queue = multiprocessing.Queue()

        if save_pictures:
            for picture_number, picture in enumerate(album_pictures):
                picture_filename = re.sub('[^\\w_\\-\\. ]', '', str(picture['pictOid']) + '.jpg')
                # If the picture doesn't already exist download it.
                if not os.path.exists(save_dir + '/' + album_dir_name + '/' + picture_filename):
                    pictures_queue.put((session,
                                        PROTO_PODHOST + "/snapfish/savemovie/PictureID=" + str(picture['pictOid']) +
                                        "_" + str(picture["ownerAcctOid"]),
                                        save_dir + '/' + album_dir_name + '/' + picture_filename))

        logger.info('Saving %i pictures (%i skipped)', pictures_queue.qsize(), len(album_pictures) - pictures_queue.qsize())
        pool.map(save_picture, list_work(pictures_queue))

    pool.close()
    pool.join()
    logger.info('Terminated.')