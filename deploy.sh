#! /bin/bash
# Deploy the app into a directory on a remote machine

PROTOCOL=http
SERVER_HOST="172.16.60.26"
REMOTE_USER="administrator"
ZIP_BASE="ai-rag-app"

function deploy {
  # unzip archive, reinstall Python requirements and restart Gunicorn
  local commit_id="$1"
  local dest_dir="$2"
  local rebuild_venv="$3"
  local archive="${ZIP_BASE}-${commit_id}.zip"

  ssh ${REMOTE_USER}@${SERVER_HOST} '
    echo "    Initializing pyenv"
    export PYENV_ROOT="$HOME/.pyenv"
    [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init - bash)"
    cd '"${dest_dir}"'
    echo "    Unzipping archive"
    rm -rf ai_rag_app config mysite
    unzip -oq '"${archive}"'
    echo '"${commit_id}"' > commit.id
    if [ "'"${rebuild_venv}"'" != "" ]; then
      echo "    Removing .venv"
      rm -rf .venv
      echo "    Creating new .venv"
      python3 -m venv .venv
      echo "    Upgrading pip"
      .venv/bin/pip install -q --upgrade pip
      echo "    Installing requirements"
      .venv/bin/pip install -q -r requirements.txt
    else
      echo "    No change to requirements.txt"
    fi
    echo "    Restarting service"
    sudo systemctl restart '"${SERVICE}"'
    echo "    Done with remote commands"'
}

TREEISH="${1:-HEAD}"

if [ "${TREEISH}" == "HEAD" ]; then
  # If we're using HEAD, we probably want everything checked in
  # Override by explicitly specifying the commit ID
  echo "Checking repo"
  if ! git diff --quiet; then
    echo 'Unstaged changes!'
    git diff --name-only
    exit 1
  fi
fi

# Ensure we have a short hash
HASH=$(git rev-parse --short "${TREEISH}^{commit}" 2> /dev/null)
if [ $? -eq 0 ]; then
  shift
else
  TREEISH="HEAD"
  HASH=$(git rev-parse --short "${TREEISH}^{commit}" 2> /dev/null)
fi

MODE="${1:-staging}"

if [ "${MODE}" == "production" ]; then
  DEST_DIR="ai-rag-app"
  SERVICE="gunicorn"
  DEST_PORT="80"
elif [ "${MODE}" == "staging" ]; then
  DEST_DIR="ai-rag-app-staging"
  SERVICE="staging"
  DEST_PORT="8000"
else
  echo "Unknown mode: ${1}"
  exit 1
fi

ARCHIVE="${ZIP_BASE}-${HASH}.zip"

echo "Deploying ${TREEISH} to ${MODE}"

if ssh "${REMOTE_USER}@${SERVER_HOST}" 'ls ' "${DEST_DIR}" ' &> /dev/null'; then
  echo "Getting current commit from ${SERVER_HOST}"
  CURRENT_COMMIT_ID=$(ssh "${REMOTE_USER}@${SERVER_HOST}" 'cat '"${DEST_DIR}/commit.id")
  if [ "${CURRENT_COMMIT_ID}" == "" ]; then
    echo "Warning: ${DEST_DIR} exists, but no current commit ID"
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
      echo "Continuing..."
    else
      echo "Aborting."
      exit 1
    fi
  else
    echo "Current commit is ${CURRENT_COMMIT_ID}"
    REBUILD_VENV=$(git diff --name-only "${HASH}" "${CURRENT_COMMIT_ID}" -- requirements.txt 2> /dev/null | head -n 1)
    if [ $? -ne 0 ]; then
      echo "Error diffing ${HASH} against ${CURRENT_COMMIT_ID} - forcing the .venv rebuild"
      REBUILD_VENV="yes"
    fi
  fi
else
  echo "Creating ${DEST_DIR} on ${SERVER_HOST}"
  ssh ${REMOTE_USER}@${SERVER_HOST} 'mkdir '"${DEST_DIR}"
fi

# Now exit on errors
set -e

echo "Zipping ${HASH} into ${ARCHIVE}"
git archive -o "${ARCHIVE}" "${HASH}"

echo "Copying archive, .env and creds"
scp -rq "${ARCHIVE}" .env creds "${REMOTE_USER}@${SERVER_HOST}:${DEST_DIR}/"

# Carry on if ssh fails so we get the service status
set +e

echo "Executing remote commands"
deploy "${HASH}" "${DEST_DIR}" "${REBUILD_VENV}"

echo "Allowing service to restart"
sleep 3

echo "Checking service status"
ssh "${REMOTE_USER}@${SERVER_HOST}" 'sudo systemctl status '"${SERVICE}"'.service'

echo "Fetching home page"

HTTP_STATUS="$(curl --max-time 60 -LI ${PROTOCOL}://${SERVER_HOST}:${DEST_PORT}/ -o /dev/null -w '%{http_code}\n' -s)"
if [ "${HTTP_STATUS}" != "200" ]; then
  echo "Error - HTTP status code ${HTTP_STATUS}"
else
  echo "Asking a question"
  HTTP_STATUS="$(curl --max-time 60 -L ${PROTOCOL}://${SERVER_HOST}:${DEST_PORT}/api/ask_question -d '{"question":"Tell me about B2"}' -H 'Content-Type: application/json' -o /dev/null -w '%{http_code}\n' -s)"
  if [ "${HTTP_STATUS}" != "200" ]; then
    echo "Error - HTTP status code ${HTTP_STATUS}"
  else
    echo "All looks ok"
    exit 0
  fi
fi

if [ "${MODE}" == "staging" ]; then
  echo "Leaving deployment in place for diagnosis"
else
  # There was an error
  if [ "${CURRENT_COMMIT_ID}" != "" ]; then
    LAST_ARCHIVE="${ZIP_BASE}-${CURRENT_COMMIT_ID}.zip"
    echo "Checking for ${LAST_ARCHIVE}"
    if ssh ${REMOTE_USER}@${SERVER_HOST} 'ls '"${DEST_DIR}/${LAST_ARCHIVE}"; then
      echo "Rolling back to ${CURRENT_COMMIT_ID}"
      deploy "${CURRENT_COMMIT_ID}" "${DEST_DIR}"
      exit 0
    fi
  fi

  echo "Cannot roll back - no last good version"
  exit 1
fi
