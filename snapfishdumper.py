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

PROTO = "https://"
HOST = "www.snapfish.com"
HOST3 = "www3.snapfish.com"
PROTO_HOST = PROTO + HOST
PROTO_HOST3 = PROTO + HOST3
MIN_PROCESSES = 1
MAX_PROCESSES = 10
DEFAULT_PROCESSES = 5
DEFAULT_VERBOSITY = 2
DEFAULT_MODE = 'all'


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
    parser = argparse.ArgumentParser(description='Snapfish albums dumper.',
                                     epilog='This software is released under GNU GPLv3 license.')
    parser.add_argument('username', metavar='username',
                        help='Snapfish login username/email')
    parser.add_argument('-p', '--password', metavar='password',
                        help='Snapfish account password. If omitted the password will be asked from stdin')
    parser.add_argument('-d', '--dir', metavar='download_dir', default=os.getcwd(),
                        help='Where to save the albums. If omitted defaults to current_dir.')
    parser.add_argument('-c', '--concurrent', default=DEFAULT_PROCESSES,
                        help='Sets the max. number of concurrent downloads (%i-%i). Default: %i' %
                             (MIN_PROCESSES, MAX_PROCESSES, DEFAULT_PROCESSES))
    parser.add_argument('-v', '--verbosity', default=DEFAULT_VERBOSITY,
                        help='Sets the verbosity threshold (1-5, lower logs more). Default: %i' % (DEFAULT_VERBOSITY, ))
    parser.add_argument('--save', choiches=['all', 'pictures', 'metadata'], dest='save', default=DEFAULT_MODE)
    parser.set_defaults(save_metadata=True)

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
    logging.basicConfig(level=log_level)

    logging.debug('Starting snapfish dumper')

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
        logging.warning('The destination directory already exists')

    if args.save == 'all':
        logging.info('Saving everything')
        save_metadata = True
        save_pictures = True
    elif args.save == 'metadata':
        logging.info('Saving only metadata')
        save_metadata = True
        save_pictures = False
    else:
        logging.info('Saving only the pictures')
        save_metadata = False
        save_pictures = True

    logging.debug('Performing authentication')
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
    auth_request_2 = session.post(PROTO_HOST3 + auth_url_2, data=auth_data_2, headers=auth_header_2)

    # TODO: check if authentication was successful

    # Get the list of the owned albums
    album_list_url = "/snapfish/fe/resources/{acct.albumListResourceUri}?accessLevel=owned"
    album_list_request = session.get(PROTO_HOST3 + album_list_url)
    album_list_json = album_list_request.text
    albums = json.loads(album_list_json)['album']

    if save_metadata:
        with open(save_dir + '/albums.json', 'w') as metadata_file:
            metadata_file.write(album_list_json.encode('utf8'))

    logging.info('Got %i albums' % (len(albums),))

    for album_number, album in enumerate(albums):
        logging.info("Downloading album %i of %i: %s", album_number + 1,
                     len(albums), album_details['albumInfo']['albumName'])

        album_details_params = {"getAlbumTags": "true",
                                "getPicOids": "true",
                                "sortOrder": "default",
                                "fromIndex": "0",
                                "itemCount": "1000"}
        album_details_request = session.get(PROTO_HOST3 + "/snapfish/fe/resources/beapi/website/snapfish_us/acct/" +
                                            str(album["ownerAcctOid"]) + "/album/" + str(album["albumOid"]) +
                                            "/granterId/" + str(album["ownerAcctOid"]) + "/albumDetail",
                                            params=album_details_params)
        album_details_json = album_details_request.text
        album_details = json.loads(album_details_json)
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
        for picture_number, picture in enumerate(album_pictures):
            picture_filename = re.sub('[^\\w_\\-\\. ]', '', str(picture['pictOid']) + '.jpg')
            # If the picture doesn't exist download it.
            if not os.path.exists(save_dir + '/' + album_dir_name + '/' + picture_filename) and save_pictures:
                pictures_queue.put((session,
                                    PROTO_HOST3 + "/snapfish/savemovie/PictureID=" + str(picture['pictOid']) +
                                    "_" + str(picture["ownerAcctOid"]),
                                    save_dir + '/' + album_dir_name + '/' + picture_filename))

        logging.info('Saving %i pictures (%i skipped)', pictures_queue.qsize(), len(album_pictures) - pictures_queue.qsize())
        pool = multiprocessing.Pool(processes=processes)
        pool.map(save_picture, list_work(pictures_queue))
        pool.close()
        pool.join()

    logging.info('Done!')