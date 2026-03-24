#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_DIR_NAME="qgis_vector_map"
PLUGIN_SRC_DIR="${ROOT_DIR}/${PLUGIN_DIR_NAME}"
METADATA_FILE="${PLUGIN_SRC_DIR}/metadata.txt"
DIST_DIR="${ROOT_DIR}/dist"
QGIS_PROFILE="${QGIS_PROFILE:-default}"
QGIS_PLUGINS_DIR="${QGIS_PLUGINS_DIR:-${HOME}/Library/Application Support/QGIS/QGIS3/profiles/${QGIS_PROFILE}/python/plugins}"
INSTALL_DIR="${QGIS_PLUGINS_DIR}/${PLUGIN_DIR_NAME}"

if [[ ! -d "${PLUGIN_SRC_DIR}" ]]; then
  echo "error: plugin source folder not found: ${PLUGIN_SRC_DIR}" >&2
  exit 1
fi

if [[ ! -f "${METADATA_FILE}" ]]; then
  echo "error: metadata file not found: ${METADATA_FILE}" >&2
  exit 1
fi

VERSION="$(awk -F= '/^version=/{print $2}' "${METADATA_FILE}" | tr -d '[:space:]')"
if [[ -z "${VERSION}" ]]; then
  echo "error: could not determine plugin version from ${METADATA_FILE}" >&2
  exit 1
fi

ZIP_PATH="${DIST_DIR}/${PLUGIN_DIR_NAME}-${VERSION}.zip"

echo "==> Building plugin zip"
mkdir -p "${DIST_DIR}"
rm -f "${ZIP_PATH}"

python3 - <<'PY' "${PLUGIN_SRC_DIR}" "${PLUGIN_DIR_NAME}" "${ZIP_PATH}"
import os
import sys
import zipfile

src_dir, root_name, zip_path = sys.argv[1], sys.argv[2], sys.argv[3]

with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for file_name in files:
            if file_name.endswith((".pyc", ".pyo")):
                continue
            full_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(full_path, src_dir)
            archive_name = os.path.join(root_name, rel_path)
            zf.write(full_path, archive_name)
PY

echo "   zip: ${ZIP_PATH}"

echo "==> Installing plugin into QGIS profile '${QGIS_PROFILE}'"
mkdir -p "${QGIS_PLUGINS_DIR}"
rm -rf "${INSTALL_DIR}"
cp -R "${PLUGIN_SRC_DIR}" "${INSTALL_DIR}"
find "${INSTALL_DIR}" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "${INSTALL_DIR}" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

echo "   install: ${INSTALL_DIR}"
echo
echo "Done. Restart QGIS or disable/enable the plugin to reload changes."
