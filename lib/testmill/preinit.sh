#
# preinit.sh: TestMill pre-initialization
#
# This script is run on a VM before any task is run. It is used to set
# up the basic test directories and helpers.  This script needs to be
# idempotent and also re-entrant with respect to any non test-specific
# state.
#
# NOTE: The contents of this script are passed through a Python
# ``.format()`` method. This means that literal left and right braces
# need to appear as '{{' and '}}' anywhere in this text, including
# in this comment.

mkdir -p bin


# Create bin/run. This is used by the "ssh" command to automatically
# start up in the right directory.

if test ! -f bin/run; then
    cat <<EOM > bin/run.$$
#!/bin/sh
testid="\$1"; cd runs
test -L "\$testid" && testid="\`readlink \"\$testid\"\`"
if test ! -d "\$testid"; then
    nm="\`ls -d \"\$testid\"* 2>/dev/null | wc -l\`"
    if test "\$nm" -eq "0"; then
        echo "Error: No such test run: \$testid"
        echo "Starting session in home directory"
    elif test "\$nm" -gt "1"; then
        echo "Error: Ambiguous test run: \$testid"
        echo "Starting session in home directory"
    else
        testid="\`ls -d \"\$testid\"*\`"
    fi
fi
test -d "\$testid" && cd "\$testid" || cd "\$HOME"
exec "\$SHELL" -l
EOM
    mv -f bin/run.$$ bin/run
    chmod 755 bin/run
fi

# Create the test run directory and the test environment.

mkdir -p sysinit
mkdir -p runs/{test_id}/.ravello
rm -f runs/last
ln -s {test_id} runs/last

# Schedule our own shutdown, and the shutdown of everybody
# else in our application.

for i in `sudo atq | awk '{{print $1}}'`; do
    sudo atrm "$i"
done
{{
    for url in {shutdown_urls}; do
        echo "curl --cookie '{api_cookie}' --request POST '$url'"
    done
    echo "shutdown -h now"
}} | sudo at "now + {keepalive} minutes"

# Finally clean ourselves up

rm -f {test_id}.preinit
