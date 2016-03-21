# DEPRECATED
SnapfishDumper no longer works. Sorry!

# SnapfishDumper
A simple Snapfish album dumper written in python.

## Usage
```
$ ./snapfishdumper.py --help
usage: snapfishdumper.py [-h] [-p password] [-d download_dir] [-c CONCURRENT]
                         [-v {1,2,3,4,5}] [-s {all,pictures,metadata}]
                         [--pod {1,2,3,4,5}]
                         username

Snapfish dumper.

positional arguments:
  username              Snapfish login username/email

optional arguments:
  -h, --help            show this help message and exit
  -p password, --password password
                        Snapfish account password. If omitted the password
                        will be asked from stdin
  -d download_dir, --dir download_dir
                        Where to save the albums.Default: current directory.
  -c CONCURRENT, --concurrent CONCURRENT
                        Sets the max. number of concurrent downloads
                        (1-10).Default: 5
  -v {1,2,3,4,5}, --verbosity {1,2,3,4,5}
                        Sets the verbosity threshold (1-5, lower logs
                        more).Default: 2
  -s {all,pictures,metadata}, --save {all,pictures,metadata}
                        Download everything, just pictures or just json
                        metadata.Default: all
  --pod {1,2,3,4,5}     Set the "pod" (server) that contains the user data. It
                        should match the number that you see in the url after
                        you log in on snapfish, eg. www3.snapfish.com => pod
                        number 3.Default: 3 (just because it works for me)

Example:
./snapfishdumper.py --dir albums --save pictures mail@provider.com

This software is released under GNU GPLv2 license.
```

## Disclaimer
I'm not in any way associated with HP or Snapfish and I do not own any right to them (*so please don't break snapfish using this software*).
