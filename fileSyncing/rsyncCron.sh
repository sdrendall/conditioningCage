#! /bin/bash

# mount server

# rsync to mac
rsync -aqz --remove-source-files ~/timelapse/ hccworkstation@10.11.36.146:~/timelapses/$HOSTNAME

# rsync to server then delete
# rsync -aqz ~/timelapse/ 
