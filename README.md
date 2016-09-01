# NdriveDAV

Virtual WebDAV server for [Naver Ndrive](http://ndrive.naver.com) service.

## Module dependency

* wsgidav
* [ndrive](http://carpedm20.github.io/ndrive)
* python-dateutil

Install the above modules first

	$ pip install wsgidav ndrive python-dateutil

## Setup Ndrive account

Modify Ndrive account in *wsgidav.conf*

	addShare("ndrive", NdriveProvider("{naver_user}", "{naver_pw}"))

Setup WebDAV password if needed

	addUser("ndrive", "{webdav_user}", "{webdav_pw}"))

## Run

	$ wsgidav --config=./wsgidav.conf

## Check in your browser

	http://{server_name}:8080/ndrive

## Known Limitation

* No Write support yet

## For more info

Visit [wiki](https://github.com/hojel/ndrivedav/wiki) for more info

