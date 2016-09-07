# KloudDAV

Virtual WebDAV server for various Cloud services

## Supported sites

* bdyun : [Baidu Yun](http://yun.baidu.com)
* ndrive : [Naver Ndrive](http://ndrive.naver.com)

## Module dependency

* wsgidav
* [ndrive](http://carpedm20.github.io/ndrive)
* python-dateutil
* py\_lru\_cache

Install the above modules first

	$ pip install wsgidav ndrive python-dateutil py_lru_cache

## Setup Ndrive account

Modify Ndrive account in *wsgidav.conf*

	addShare("ndrive", NdriveProvider("{naver_user}", "{naver_pw}"))

Setup WebDAV password if needed

	addUser("ndrive", "{webdav_user}", "{webdav_pw}"))

## Run

	$ wsgidav --config=./wsgidav.conf

## Check in your browser

	http://{server_name}:8080/ndrive

## For more info

Visit [wiki](https://github.com/hojel/klouddav/wiki) for more info

Baidu cloud API is obtained from [Kodi bdyun plugin](https://github.com/caasiu/plugin.video.bdyun)

