#!/bin/sh
#
# Perform checks on the standard images.

errors=0

add_error() {
    errors="`expr $errors + 1`"
}

# Environment variables

test_envvars() {
    type="$1"; shift
    for name in $*; do
        eval value="\$$name"
        if test -z "$value"; then
            echo "[$type]: Variable not set: $name"
            add_error
        fi
    done
}

test_envvars "Environment" RAVELLO_TEST_ID RAVELLO_TEST_USER RAVELLO_APP_ID \
        RAVELLO_APP_NAME RAVELLO_APPDEF_NAME RAVELLO_PROJECT \
        RAVELLO_SERVICE_URL RAVELLO_SERVICE_COOKIE RAVELLO_VM_ID \
        RAVELLO_VM_NAME

# User "ravello" settings

username="`id -un`"
if test "$username" != "ravello"; then
    echo "[Default user]: My username is not ravello: $username"
    add_error
fi

sudo -n true 2>/dev/null
if test "$?" -ne "0"; then
    echo "[Default user]: Password-less sudo is not available."
    add_error
fi

# Commands

find_commands() {
    type="$1"; shift
    for cmd in $*; do
        command="`which $cmd 2>/dev/null`"
        if test -z "$command" -o ! -x "$command"; then
            echo "[$type]: Command not found: $cmd"
            add_error
        fi
    done
}

find_commands "Base OS" gcc g++ make locate at tar gzip bzip2 \
    git hg svn python easy_install pip nosetests virtualenv

case "$RAVELLO_VM_NAME" in
    fedora16|fedora17|fedora18|ubuntu1204|ubuntu1210)
        find_commands "Python3 Stack" python3 easy_install3 pip3 nosetests3 \
                virtualenv3
        find_commands "Java Stack" java javac mvn ant
        find_commands "Clojure Stack" lein
        ;;
    *)
        ;;
esac

test "$errors" -gt "0" && exit 1 || exit 0
