# -*- makefile -*-

# This is a simple makefile which lives in a buildmaster/buildslave
# directory (next to the buildbot.tac file). It allows you to start/stop the
# master or slave by doing 'make start' or 'make stop'.

# The 'reconfig' target will tell a buildmaster to reload its config file.

start:
	twistd --no_save -y buildbot.tac

stop:
	kill `cat twistd.pid`

reconfig:
	kill -HUP `cat twistd.pid`

log:
	tail -f twistd.log

# ---------------------------------------------------------------
# manual editing of the automatically generated Makefile
#
debug:
	twistd --no_save -n -b --logfile=- -y buildbot.tac
#
# ---------------------------------------------------------------
