import logging
import numbers
import os
import shutil
import uuid
from os import makedirs
from os.path import split, join, basename, splitext, exists, dirname, normpath, getsize
from typing import Any, List, Tuple, cast

import pandas as pd


def create_file(filename, content):
    with open(filename, 'w') as f:
        f.write(content)


def sanitize_media_path_value(path_value: Any) -> str:
    if pd.isna(path_value):
        return ''

    if isinstance(path_value, str):
        return path_value.strip()

    if isinstance(path_value, os.PathLike):
        normalized_path = os.fspath(path_value)
        if isinstance(normalized_path, bytes):
            return normalized_path.decode().strip()

        return normalized_path.strip()

    if isinstance(path_value, numbers.Number):
        return ''

    return str(path_value).strip()


def sanitize_media_path_column(df: pd.DataFrame, path_key: str) -> pd.DataFrame:
    df[path_key] = df[path_key].apply(sanitize_media_path_value)
    return df

def get_folder_structure(filepath: Any, copy_files_dir_level: int) -> str:
    filepath = sanitize_media_path_value(filepath)
    folders: List[str] = []
    while True:
        filepath, folder = split(filepath)
        if folder != "":
            folders.append(folder)
        else:
            if filepath != "":
                folders.append(filepath)
            break

    wanted_folder_structure: List[str] = folders[1:1 + copy_files_dir_level]
    if not wanted_folder_structure:
        return ''

    return cast(str, join(*wanted_folder_structure))


def copy_files_to_output_dir(df: pd.DataFrame, path_key: str, output_folder: str,
                             used_paths: List[str], copy_files_dir_level: int) -> Tuple[pd.DataFrame, List[str]]:
    df = sanitize_media_path_column(df, path_key)

    for raw_src_path in df[path_key].unique():
        src_path = cast(str, sanitize_media_path_value(raw_src_path))

        if src_path == '':
            logging.warning(f'Warning: empty path. Skipping copy.')
            continue

        if not exists(src_path):
            logging.warning(f'Warning: {src_path} does not exist. Skipping copy.')
            continue

        filename = cast(str, basename(src_path))
        folder_structure_to_copy = cast(str, get_folder_structure(src_path, copy_files_dir_level))

        target_path = cast(str, join(output_folder, 'data', folder_structure_to_copy, filename))
        logging.debug(f'copy {src_path} to {target_path}')

        if target_path in used_paths:
            logging.warning(f'Warning: filename {filename} already used. Adding unique id to filename.')
            filename_no_ext, ext = splitext(filename)
            filename = f'{filename_no_ext}_{uuid.uuid4()}{ext}'
            target_path = cast(str, join(output_folder, 'data', folder_structure_to_copy, filename))

        used_paths.append(target_path)

        if not exists(dirname(target_path)):
            makedirs(dirname(target_path))

        # check if paths are the same, also incorporating e.g. ./ at the beginning
        if normpath(src_path) == normpath(target_path):
            logging.warning('Warning: src and target path are the same. Skipping copy.')
            continue

        # check if file exists already, if so, check if it has the same size
        # if equal, skip copy
        if exists(target_path) and (getsize(src_path) == getsize(target_path)):
            logging.info(f'Info: {target_path} already exists and has the same size. Skipping copy.')
        else:
            shutil.copyfile(src_path, target_path)

        # update old path to new relative path 'data/...'
        target_path_relative = cast(str, join('data', folder_structure_to_copy, filename))

        # escape # in the path
        df[path_key] = df[path_key].replace(src_path, target_path_relative)

    return df, used_paths
