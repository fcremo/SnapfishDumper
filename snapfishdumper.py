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

PROTO = "https://"
HOST = "www.snapfish.com"
HOST3 = "www3.snapfish.com"
PROTO_HOST = PROTO + HOST
PROTO_HOST3 = PROTO + HOST3
MIN_PROCESSES = 1
MAX_PROCESSES = 10
DEFAULT_PROCESSES = 5


def list_work(queue):
    """ Use a queue to distribute the jobs to the subprocesses """
    for i in range(0, queue.qsize()):
        yield queue.get()


def save_picture((session, url, path)):
    with open(path, 'wb') as handle:
        response = session.get(url, stream=True)

        if not response.ok:
            print "Error downloading" + url

        for block in response.iter_content(4096):
            if not block:
                break
            handle.write(block)


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
    parser.add_argument('--dont-save-metadata', dest='save_metadata', action='store_false')
    parser.set_defaults(save_metadata=True)

    args = parser.parse_args()

    username = args.username

    if args.dir.startswith('/'):
        save_dir = args.dir
    else:
        save_dir = os.getcwd() + '/' + args.dir
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)

    if args.password is None:
        password = getpass.getpass("Snapfish account password: ")
    else:
        password = args.password

    if MIN_PROCESSES <= int(args.concurrent) <= MAX_PROCESSES:
        processes = int(args.concurrent)
    else:
        print("Choose a number of concurrent downloads between %i and %i!" % (MIN_PROCESSES, MAX_PROCESSES))
        exit()

    save_metadata = args.save_metadata

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

    # Get the list of the owned albums
    album_list_url = "/snapfish/fe/resources/{acct.albumListResourceUri}?accessLevel=owned"
    album_list_request = session.get(PROTO_HOST3 + album_list_url)
    album_list_json = album_list_request.text

    if save_metadata:
        with open(save_dir + '/albums.json', 'w') as metadata_file:
            metadata_file.write(album_list_json.encode('utf8'))

    albums = json.loads(album_list_json)['album']
    for album_number, album in enumerate(albums):
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

        print "Downloading album %i of %i: %s" % (
            album_number + 1, len(albums), album_details['albumInfo']['albumName'])

        album_dir_name = re.sub('[^\\w_\\-\\. ]', '', album_details['albumInfo']['albumName'])
        try:
            os.mkdir(save_dir + '/' + album_dir_name)
        except OSError:
            # Error: There are more albums with the same name, use the album ID to distinguish them
            album_dir_name = album_dir_name + '_' + str(album_details['albumInfo']['albumOid'])
            os.mkdir(save_dir + '/' + album_dir_name)

        if save_metadata:
            with open(save_dir + '/' + album_dir_name + '/album.json', 'w') as metadata_file:
                metadata_file.write(album_details_json.encode('utf8'))

        pictures_queue = multiprocessing.Queue()
        for picture_number, picture in enumerate(album_pictures):
            picture_filename = re.sub('[^\\w_\\-\\. ]', '', str(picture['pictOid']) + '.jpg')
            pictures_queue.put((session,
                                PROTO_HOST3 + "/snapfish/savemovie/PictureID=" + str(picture['pictOid']) +
                                "_" + str(picture["ownerAcctOid"]),
                                save_dir + '/' + album_dir_name + '/' + picture_filename))

        pool = multiprocessing.Pool(processes=processes)
        pool.map(save_picture, list_work(pictures_queue))