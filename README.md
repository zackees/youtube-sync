# youtube-sync

Syncs up your youtube or other channels data to the hard drive. A library.json file will be created to track which videos have already been found. It will download any missing files.

# Docker Setup

You will need to have `config.json` embedded at the root of the container. Render.com makes this easy with a secret file.

If you do not have the ability to inject a file at the root, stash your json as a one liner into env variable "YOUTUBE_SYNC_CONFIG_JSON"

# Config.json

This configuration holds the rclone configuration as well as the channel setup and destination root. There is no type checking for the rclone section, instead
just list the key value pairs as shown below.

```json
{
    "output": "dst:Bucket/root/path",
    "rclone": {
        "dst": {
            "type": "b2",
            "account": "****",
            "key": "****"
        }
    },
    "channels": [
        {
            "name": "RonGibson",
            "source": "brighteon",
            "channel_id": "rongibsonchannel"
        },
        {
            "name": "TheDuran",
            "source": "youtube",
            "channel_id": "@theduran"
        }
    ]
}
```

In this case the files will be outputted to

  * RonGibson -> dst:path/to/RonGibson/brighteon/*
  * TheDuran -> dst:path/to/TheDuran/youtube/*

Each output directory will have one `library.json` file an multiple mp3 files.



# PO Token TODO:

  * https://github.com/LuanRT/BgUtils
  * https://github.com/iv-org/youtube-trusted-session-generator
    * docker run -p 8080:8080 quay.io/invidious/youtube-trusted-session-generator:webserver