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

PROTO = "https://"
HOST = "www.snapfish.com"
HOST3 = "www3.snapfish.com"
PROTO_HOST = PROTO + HOST
PROTO_HOST3 = PROTO + HOST3

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Snapfish albums dumper.',
                                     epilog='This software is released under GNU GPLv3')
    parser.add_argument('username', metavar='username',
                        help='Snapfish login username/email')
    parser.add_argument('-p', '--password', metavar='password',
                        help='Snapfish account password. If omitted the password will be asked from stdin')
    parser.add_argument('-d', '--dir', metavar='download_dir', default=os.getcwd(),
                        help='Where to save the albums. If omitted defaults to current_dir.')

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

    session = requests.session()
    headers = {"Origin": PROTO_HOST,
               "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/41.0.2272.76 Safari/537.36"}
    session.headers.update(headers)

    # initialRequest = session.get(PROTO_HOST + "/photo-gift/welcome")

    # Perform authentication
    authURL = "/snapfish/loginsubmit/fromTS=true/module=true/" \
              "topWindowHost=www.snapfish.com/istws=true/pns/snapfish/welcome"
    authData = {"avoidDomainValidation": "true",
                "emailaddress": username,
                "password": password,
                "log in.x": 10,
                "log in.y": 15}
    authHeader = {"Referer": PROTO_HOST + "/snapfish/login/fromTS=true/module=true/"
                                          "topWindowHost=www.snapfish.com/istws=true//pns/"}
    authRequest = session.post(PROTO_HOST + authURL, data=authData, headers=authHeader)

    authURL2 = "/snapfish/loginsubmit/fromTS=true/module=true/" \
               "topWindowHost=www.snapfish.com/istws=true/pns/snapfish/welcome"
    authData2 = {"retuser": "FALSE",
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
    authHeader2 = {"Referer": PROTO_HOST + "/snapfish/loginsubmit/fromTS=true/module=true/"
                                           "topWindowHost=www.snapfish.com/istws=true/pns/snapfish/welcome"}
    authRequest2 = session.post(PROTO_HOST3 + authURL2, data=authData2, headers=authHeader2)

    albumListURL = "/snapfish/fe/resources/{acct.albumListResourceUri}?accessLevel=owned"
    albumListRequest = session.get(PROTO_HOST3 + albumListURL)
    albumListJSON = albumListRequest.text

    with open(save_dir + '/albums.json', 'w') as metadataFile:
        metadataFile.write(albumListJSON.encode('utf8'))

    albums = json.loads(albumListJSON)['album']
    for albumNumber, album in enumerate(albums):
        albumDetailsParams = {"getAlbumTags": "true",
                              "getPicOids": "true",
                              "sortOrder": "default",
                              "fromIndex": "0",
                              "itemCount": "1000"}
        albumDetailsRequest = session.get(PROTO_HOST3 + "/snapfish/fe/resources/beapi/website/snapfish_us/acct/" +
                                          str(album["ownerAcctOid"]) + "/album/" + str(album["albumOid"]) +
                                          "/granterId/" + str(album["ownerAcctOid"]) + "/albumDetail",
                                          params=albumDetailsParams)
        albumDetailsJSON = albumDetailsRequest.text
        albumDetails = json.loads(albumDetailsJSON)
        albumPictures = albumDetails['userAssets']['userAsset']

        albumDirName = re.sub('[^\\w_\\-\\. ]', '', albumDetails['albumInfo']['albumName'])
        try:
            os.mkdir(save_dir + '/' + albumDirName)
        except OSError:
            # There are more albums with the same name, use the album ID to distinguish them
            albumDirName = albumDirName + '_' + str(albumDetails['albumInfo']['albumOid'])
            os.mkdir(save_dir + '/' + albumDirName)
        with open(save_dir + '/' + albumDirName + '/album.json', 'w') as metadataFile:
            metadataFile.write(albumDetailsJSON.encode('utf8'))

        for picture in albumPictures:
            pictureFileName = re.sub('[^\\w_\\-\\. ]', '', str(picture['pictOid']) + '.jpg')
            with open(save_dir + '/' + albumDirName + '/' + pictureFileName, 'wb') as handle:
                response = session.get(PROTO_HOST3 + "/snapfish/savemovie/PictureID=" + str(picture['pictOid']) + "_" +
                                       str(picture["ownerAcctOid"]), stream=True)

                if not response.ok:
                    print "Error downloading image " + str(picture["pictOid"])

                for block in response.iter_content(4096):
                    if not block:
                        break
                    handle.write(block)