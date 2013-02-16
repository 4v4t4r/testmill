#
# Driver to run shell commands.

broadcast() {{
    local value
    eval value="\$$1"
    echo "$1 $value" >> $RAVELLO_ENV_UPDATE
}}

{shell_vars}

# eval to perform '~' expansion
eval RAVELLO_HOME=~$RAVELLO_TEST_USER
RAVELLO_TEST_DIR=$RAVELLO_HOME/runs/$RAVELLO_TEST_ID
RAVELLO_ENV_UPDATE=$RAVELLO_TEST_DIR/.ravello/$RAVELLO_TASK_NAME.env-update

cd $RAVELLO_TEST_DIR

touch $RAVELLO_ENV_UPDATE
chmod 644 $RAVELLO_ENV_UPDATE

{shell_commands}

exit 0
